from __future__ import annotations

import json
from typing import Annotated, TypedDict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.tools.log_tools import search_logs_tool, aggregate_logs_tool
from app.tools.dashboard_tools import generate_dashboard_tool
from app.tools.rag_tools import rag_search_tool

class EnterpriseAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [
    search_logs_tool,
    aggregate_logs_tool,
    rag_search_tool,
    generate_dashboard_tool,
]

llm = ChatGoogleGenerativeAI(
    model=settings.chat_model,
    google_api_key=settings.google_api_key,
    temperature=0,
    max_output_tokens=settings.max_output_tokens,
)

llm_with_tools = llm.bind_tools(tools)

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

    response = await llm_with_tools.ainvoke(
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

enterprise_agent_graph = graph.compile()

async def run_enterprise_agent(question: str) -> dict[str, Any]:
    result = await enterprise_agent_graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=question)
            ]
        }
    )

    messages = result["messages"]
    final_message = messages[-1]

    structured_outputs = extract_structured_outputs(messages)
    
    return {
        "answer": str(final_message.content),
        **structured_outputs
    }

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
    logs: list[dict[str, Any]] = []
    aggregations: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    dashboard: dict[str, Any] | None = None

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        tool_name = message.name or "unknown_tool"
        tool_calls.append(tool_name)

        data = _safe_json_loads(str(message.content))

        if tool_name == "search_logs_tool":
            logs.extend(data.get("logs", []))

        elif tool_name == "aggregate_logs_tool":
            aggregations.append(
                {
                    "field": data.get("field"),
                    "buckets": data.get("buckets", []),
                }
            )

        elif tool_name == "rag_search_tool":
            sources.extend(data.get("sources", []))

        elif tool_name == "generate_dashboard_tool":
            dashboard = data.get("dashboard")

    return {
        "tool_calls": tool_calls,
        "logs": logs,
        "aggregations": aggregations,
        "sources": sources,
        "dashboard": dashboard,
    }
