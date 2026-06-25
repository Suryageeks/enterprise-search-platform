from __future__ import annotations

import json
from typing import Annotated, TypedDict, Any
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.tools.log_tools import search_logs_tool, aggregate_logs_tool
from app.tools.dashboard_tools import generate_dashboard_tool
from app.tools.rag_tools import rag_search_tool
from app.services.llm_service import llm_service
from app.services.tool_result_service import (
    build_warnings,
    calculate_agent_status,
    parse_tool_result,
)
from app.prompts.enterprise_agent import (
    ENTERPRISE_AGENT_PROMPT,
)
from app.schemas.domain import (
    DomainClassification,
    DomainDecision,
)
from app.services.domain_classifier_service import (
    domain_classifier_service,
)
from app.services.evidence_service import (
    collect_evidence,
    messages_have_evidence,
)
from app.services.remediation_renderer import render_remediation
from app.services.remediation_service import (
    RemediationGenerationError,
    remediation_service,
)

enterprise_agent_graph: CompiledStateGraph | None = None
MAX_TOOL_ROUNDS = 3

class EnterpriseAgentState(TypedDict, total = False):
    messages: Annotated[list[BaseMessage], add_messages]
    classification: dict[str, Any]
    remediation: dict[str, Any] | None
    tool_rounds: int

tools = [
    search_logs_tool,
    aggregate_logs_tool,
    rag_search_tool,
    generate_dashboard_tool,
]

async def call_model(state: EnterpriseAgentState) -> EnterpriseAgentState:
    classification = DomainClassification.model_validate(
        state["classification"]
    )

    policy_content = {
        "decision": classification.decision,
        "requires_evidence": (
            classification.requires_evidence
        ),
        "allow_code_solution": (
            classification.allow_code_solution
        )
    }

    system_message = SystemMessage(
        content = (
             ENTERPRISE_AGENT_PROMPT
            + "\n\nCURRENT POLICY:\n"
            + json.dumps(policy_content)
        )
    )

    tool_rounds = state.get("tool_rounds", 0)
    messages = [system_message, *state["messages"]]

    if tool_rounds >= MAX_TOOL_ROUNDS:
        response = await llm_service.ainvoke(
            [
                SystemMessage(
                    content=(
                        f"{system_message.content}\n\n"
                        "TOOL LIMIT REACHED:\n"
                        "Do not request another tool. Produce the final answer "
                        "using only evidence already returned in this turn."
                    )
                ),
                *state["messages"],
            ]
        )
        response = AIMessage(
            content=(
                extract_message_text(response.content).strip()
                or render_tool_limit_answer(state["messages"])
            )
        )
    else:
        response = await llm_service.ainvoke_with_tools(tools, messages)

    has_tool_calls = bool(
        getattr(response,"tool_calls", None)
    )

    if (classification.requires_evidence 
        and not has_tool_calls 
        and not messages_have_evidence(
            current_turn_messages(state["messages"])
        )
    ):
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I could not find sufficient authorized "
                        "log or document evidence to answer this request."
                    )
                )
            ]
        }

    return {
        "messages": [response],
        "tool_rounds": tool_rounds + int(has_tool_calls),
    }


def render_tool_limit_answer(messages: list[BaseMessage]) -> str:
    evidence = collect_evidence(current_turn_messages(messages))
    logs = [item for item in evidence if item.get("type") == "log"]
    aggregations = [
        item for item in evidence if item.get("type") == "aggregation"
    ]

    if not evidence:
        return (
            "No relevant authorized evidence was found before the tool-call "
            "limit was reached."
        )

    lines = [
        "### Summary",
        "The search completed with retrieved evidence.",
        "",
        "### Evidence",
    ]

    for log in logs[:5]:
        identity = log.get("trace_id") or log.get("request_id") or "no trace ID"
        lines.append(
            "- "
            f"{log.get('service') or 'unknown service'} "
            f"[{log.get('status_code') or log.get('level') or 'unknown status'}]: "
            f"{log.get('message') or 'No message'} ({identity})"
        )

    for aggregation in aggregations[:2]:
        buckets = ", ".join(
            f"{bucket.get('key')}: {bucket.get('count')}"
            for bucket in aggregation.get("buckets", [])[:8]
        )
        lines.append(f"- {aggregation.get('field')}: {buckets}")

    lines.extend(
        [
            "",
            "### Limitation",
            "Further tool calls were stopped after the safe per-request limit.",
        ]
    )
    return "\n".join(lines)

def should_continue(state: EnterpriseAgentState) -> str:
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END

'''
Classification Node
'''
def latest_user_question(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return extract_message_text(
                message.content
            )
    raise ValueError("No user question found")

def conversation_context(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    context = []

    for message in messages[-8:]:
        if isinstance(message, ToolMessage):
            continue

        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue

        context.append(
            {
                "role": role,
                "content": extract_message_text(
                    message.content
                )[:2000],
            }
        )
    
    return context

async def classify_request(state: EnterpriseAgentState) -> EnterpriseAgentState:
    classification = (
        await domain_classifier_service.classify(
            question=latest_user_question(
                state["messages"]
            ),
            conversation_context=conversation_context(
                state["messages"][:-1]
            ),
        )
    )

    return {
        "classification": (
            classification.model_dump(mode="json")
        ),
        "remediation": None,
        "tool_rounds": 0,
    }


'''
Refusal Node
'''
async def refusal_request(state: EnterpriseAgentState) -> EnterpriseAgentState:
    classification = DomainClassification.model_validate(
        state["classification"]
    )

    if (classification.decision == DomainDecision.UNSAFE):
        answer = (
            "I cannot perform data modification, arbitrary "
            "database/OpenSearch operations, or script execution. "
            "I can only search and analyze authorized operational data."
        )
    else:
        answer = (
            "I can only answer questions related to authorized logs, "
            "incidents, runbooks, operational dashboards, and fixes "
            "supported by retrieved error evidence."
        )

    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }

'''
Source/Grounding Validation
'''

def current_turn_messages(
    messages: list[BaseMessage],
) -> list[BaseMessage]:
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index:]

    return []

async def validate_grounding(
    state: EnterpriseAgentState,
) -> EnterpriseAgentState:
    classification = DomainClassification.model_validate(
        state["classification"]
    )

    if not classification.requires_evidence:
        return {"messages": []}

    if messages_have_evidence(current_turn_messages(state["messages"])):
        return {"messages": []}

    return {
        "messages": [
            AIMessage(
                content=(
                    "No relevant authorized evidence was found. "
                    "I cannot provide a diagnosis or code solution "
                    "without supporting logs, runbooks, or incident data."
                )
            )
        ]
    }


async def generate_remediation(
    state: EnterpriseAgentState,
) -> EnterpriseAgentState:
    classification = DomainClassification.model_validate(
        state["classification"]
    )
    evidence = collect_evidence(current_turn_messages(state["messages"]))

    if not evidence:
        return {
            "remediation": None,
            "messages": [
                AIMessage(
                    content=(
                        "No relevant authorized evidence was found. I cannot "
                        "provide a diagnosis or code solution."
                    )
                )
            ],
        }

    try:
        result = await remediation_service.generate(
            question=latest_user_question(state["messages"]),
            evidence=evidence,
            allow_code_solution=classification.allow_code_solution,
        )
    except RemediationGenerationError:
        return {
            "remediation": None,
            "messages": [
                AIMessage(
                    content=(
                        "Evidence was found, but I could not generate a "
                        "validated remediation plan."
                    )
                )
            ],
        }

    return {
        "remediation": result.model_dump(mode="json"),
        "messages": [AIMessage(content=render_remediation(result))],
    }

'''
Graph Routing
'''
def route_after_classification(
    state: EnterpriseAgentState,
) -> str:
    classification = DomainClassification.model_validate(
        state["classification"]
    )

    if classification.decision in {
        DomainDecision.OUT_OF_DOMAIN,
        DomainDecision.UNSAFE
    }:
        return "refuse"
    
    return "agent"

def route_after_agent(
    state: EnterpriseAgentState,
) -> str:
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    classification = DomainClassification.model_validate(
        state["classification"]
    )
    if classification.decision == DomainDecision.REMEDIATION:
        return "remediation"

    return "validate_grounding"

graph = StateGraph(EnterpriseAgentState)

graph.add_node("classify_request",classify_request)
graph.add_node("refuse",refusal_request)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_node("validate_grounding",validate_grounding)
graph.add_node("remediation", generate_remediation)

graph.set_entry_point("classify_request")

graph.add_conditional_edges(
    "classify_request",
    route_after_classification,
    {
        "refuse": "refuse",
        "agent": "agent",
    }
)

graph.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "tools": "tools",
        "remediation": "remediation",
        "validate_grounding": (
            "validate_grounding"
        ),
    }
)

graph.add_edge("tools", "agent")
graph.add_edge("remediation", "validate_grounding")
graph.add_edge("refuse", END)
graph.add_edge("validate_grounding", END)

# enterprise_agent_graph = graph.compile()

def initialize_enterprise_agent_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    global enterprise_agent_graph

    enterprise_agent_graph = graph.compile(
        checkpointer=checkpointer
    )

    return enterprise_agent_graph

def get_enterprise_agent_graph() -> CompiledStateGraph:
    if enterprise_agent_graph is None:
        raise RuntimeError(
            "Enterprise agent graph has not been initialized"
        )
    
    return enterprise_agent_graph


async def delete_enterprise_agent_thread(thread_id: str) -> None:
    compiled_graph = get_enterprise_agent_graph()
    checkpointer = compiled_graph.checkpointer

    if checkpointer is None:
        return

    await checkpointer.adelete_thread(thread_id)

async def run_enterprise_agent(
        question: str,
        thread_id: str
    ) -> dict[str, Any]:

    compiled_graph = get_enterprise_agent_graph()

    current_message = HumanMessage(
        id=str(uuid4()),
        content=question
    )

    result = await compiled_graph.ainvoke(
        {
            "messages": [current_message]
        },
        config={
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )

    all_messages = result["messages"]

    turn_messages = messages_from_current_turn(
        messages=all_messages,
        current_message_id=current_message.id
    )

    final_message = turn_messages[-1]

    structured = extract_structured_outputs(turn_messages)
    structured["remediation"] = result.get("remediation")

    return {
        "answer": extract_message_text(final_message.content),
        **structured,
    }

def messages_from_current_turn(
    messages: list[BaseMessage],
    current_message_id: str
) -> list[BaseMessage]:
    for index, message in enumerate(messages):
        if message.id == current_message_id:
            return messages[index:]

    raise RuntimeError("Current user message was not found in graph state")

def extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])

        return "\n\n".join(parts)

    return str(content)

def _safe_json_loads(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if isinstance(data, dict):
        return data
    return {}

def extract_structured_outputs(messages: list[BaseMessage]) -> dict[str, Any]:
    tool_calls: list[str] = []
    tool_results = []
    logs = []
    aggregations = []
    sources = []
    dashboard = None

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        tool_name = message.name or "unknown_tool"
        tool_calls.append(tool_name)

        result = parse_tool_result(str(message.content))

        if result is None:
            continue

        tool_results.append(result)

        if result.data is None:
            continue

        if tool_name == "search_logs_tool":
            logs.extend(result.data.get("logs", []))

        elif tool_name == "aggregate_logs_tool":
            aggregations.append(
                {
                    "field": result.data.get("field"),
                    "buckets": result.data.get("buckets", []),
                }
            )

        elif tool_name == "rag_search_tool":
            sources.extend(result.data.get("sources", []))

        elif tool_name == "generate_dashboard_tool":
            dashboard = result.data.get("dashboard")

    status = calculate_agent_status(tool_results)

    return {
        "status": status,
        "tool_calls": tool_calls,
        "tool_results": [
            result.model_dump(mode="json")
            for result in tool_results
        ],
        "warnings": build_warnings(tool_results),
        "logs": logs,
        "aggregations": aggregations,
        "sources": sources,
        "dashboard": dashboard,
    }
