from __future__ import annotations

import json
from typing import Annotated, TypedDict, Any
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
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

enterprise_agent_graph: CompiledStateGraph | None = None

class EnterpriseAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [
    search_logs_tool,
    aggregate_logs_tool,
    rag_search_tool,
    generate_dashboard_tool,
]

async def call_model(state: EnterpriseAgentState) -> EnterpriseAgentState:
    system_message = SystemMessage(
        content="""
            You are an Enterprise Log Intelligence Agent.

            You can use tools to answer questions across logs, dashboards, and internal knowledge.

            Available tool behavior:
            - search_logs_tool: find specific log events in OpenSearch.
            - aggregate_logs_tool: group/count logs by service, endpoint, level, status code, exception type.
            - rag_search_tool: search internal documents, runbooks, and knowledge base content.
            - generate_dashboard_tool: generate chart-ready dashboards for log analytics.

            Rules:
            - Use tools when the answer needs real data.
            - Do not invent logs, sources, dashboards, counts, trace IDs, or services.
            - For "create dashboard", "visualize", "chart", or "graph", call generate_dashboard_tool.
            - For "what do docs/runbooks say", call rag_search_tool.
            - For "did this happen", "show logs", "find errors", call search_logs_tool.
            - For "by service", "top endpoints", "count by status", call aggregate_logs_tool.
            - You may call multiple tools if the question needs multiple capabilities.
            - After tool calls, provide a concise final answer.
        """
    )

    response = await llm_service.ainvoke_with_tools(
        tools,
        [system_message, *state["messages"]]
    )

    return {
        "messages": [response]
    }

def should_continue(state: EnterpriseAgentState) -> str:
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END

graph = StateGraph(EnterpriseAgentState)

graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))

graph.set_entry_point("agent")

graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

graph.add_edge("tools", "agent")

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

    return {
        "answer": extract_message_text(final_message.content),
        **extract_structured_outputs(turn_messages),
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
