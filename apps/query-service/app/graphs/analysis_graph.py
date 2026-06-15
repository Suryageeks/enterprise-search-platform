from __future__ import annotations

from typing import Literal, TypedDict, Any

from langgraph.graph import END, StateGraph

from app.schemas.rag import RagSource
from app.services.rag_service import rag_service
from app.schemas.logs import LogAggregation, LogEvidence
from app.services.log_agent_service import log_agent_service
from app.schemas.dashboard import DashboardSpec, ExecutedDashboard
from app.services.dashboard_agent_service import dashboard_agent_service


Intent = Literal[
    "RAG_QUERY",
    "LOG_QUERY",
    "DASHBOARD_QUERY",
    "MULTI_AGENT_QUERY",
    "UNSUPPORTED",
]


class AnalysisGraphState(TypedDict, total=False):
    question: str
    top_k: int

    intent: Intent

    answer: str
    sources: list[RagSource]
    used_context: bool

    evidence: list[LogEvidence]
    aggregations: list[LogAggregation]
    dashboard: DashboardSpec | ExecutedDashboard | None

    error: str


async def classify_intent(state: AnalysisGraphState) -> AnalysisGraphState:
    question = state["question"].lower()

    dashboard_words = ["dashboard", "chart", "graph", "visualize", "plot", "charts", "graphs", "visualize", "plots", "widget", "panel", "report"]
    log_words = ["log", "logs", "error", "errors", "trace", "status code", "5xx", "4xx"]

    if any(word in question for word in dashboard_words):
        intent: Intent = "DASHBOARD_QUERY"
    elif any(word in question for word in log_words):
        intent = "LOG_QUERY"
    else:
        intent = "RAG_QUERY"

    return {
        **state,
        "intent": intent,
    }


def route_by_intent(state: AnalysisGraphState) -> str:
    intent = state.get("intent")

    if intent == "RAG_QUERY":
        return "rag_agent"
    
    if intent == "LOG_QUERY":
        return "log_agent"

    if intent == "DASHBOARD_QUERY":
        return "dashboard_agent"

    return "unsupported_agent"


async def rag_agent(state: AnalysisGraphState) -> AnalysisGraphState:
    result = await rag_service.query(
        question=state["question"],
        top_k=state.get("top_k", 5),
    )

    return {
        **state,
        "answer": result.answer,
        "sources": result.sources,
        "used_context": result.used_context,
    }

async def log_agent(state: AnalysisGraphState) -> AnalysisGraphState:
    result = await log_agent_service.answer_log_question(
        question=state["question"],
        size=10,
    )

    return {
        **state,
        "answer": result.answer,
        "evidence": result.evidence,
        "aggregations": result.aggregations,
        "sources": [],
        "used_context": False,
    }

async def dashboard_agent(state: AnalysisGraphState) -> AnalysisGraphState:
    result = await dashboard_agent_service.generate_dashboard(
        question=state["question"]
    )

    return {
        **state,
        "answer": result.answer,
        "dashboard": result.dashboard,
        "sources": [],
        "used_context": False,
        "evidence": [],
        "aggregations": [],
    }


async def unsupported_agent(state: AnalysisGraphState) -> AnalysisGraphState:
    intent = state.get("intent", "UNSUPPORTED")

    return {
        **state,
        "answer": f"{intent} is not implemented yet. Currently only RAG_QUERY is supported.",
        "sources": [],
        "used_context": False,
    }


def create_analysis_graph():
    graph = StateGraph(AnalysisGraphState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("log_agent", log_agent)
    graph.add_node("dashboard_agent", dashboard_agent)
    graph.add_node("unsupported_agent", unsupported_agent)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "rag_agent": "rag_agent",
            "log_agent": "log_agent",
            "dashboard_agent": "dashboard_agent",
            "unsupported_agent": "unsupported_agent",
        },
    )

    graph.add_edge("rag_agent", END)
    graph.add_edge("log_agent", END)
    graph.add_edge("dashboard_agent", END)
    graph.add_edge("unsupported_agent", END)

    return graph.compile()


analysis_graph = create_analysis_graph()


async def run_analysis_graph(
    question: str,
    top_k: int = 5,
) -> AnalysisGraphState:
    return await analysis_graph.ainvoke(
        {
            "question": question,
            "top_k": top_k,
        }
    )
