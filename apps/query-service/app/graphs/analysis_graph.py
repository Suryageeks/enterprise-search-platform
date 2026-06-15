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
    log_words = ["log","logs","error","errors","trace","status code","5xx","4xx","failure","failed","fail","exception","timeout"]
    analysis_words = ["why","analyze","analysis","root cause","investigate","explain","what happened"]

    wants_dashboard = any(word in question for word in dashboard_words)
    wants_logs = any(word in question for word in log_words)
    wants_analysis = any(word in question for word in analysis_words)

    if wants_dashboard and (wants_logs or wants_analysis):
        intent: Intent = "MULTI_AGENT_QUERY"
    elif wants_dashboard:
        intent: Intent = "DASHBOARD_QUERY"
    elif wants_logs:
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
    
    if intent == "MULTI_AGENT_QUERY":
        return "multi_agent"

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

async def multi_agent(state: AnalysisGraphState) -> AnalysisGraphState:
    question = state["question"]

    log_result = None
    dashboard_result = None

    errors: list[str] = []

    try:
        log_result = await log_agent_service.answer_log_question(
            question=question,
            size=10,
        )
    except Exception as exc:
        errors.append(f"Log Agent failed: {exc}")

    try:
        dashboard_result = await dashboard_agent_service.generate_dashboard(
            question=question
        )
    except Exception as exc:
        errors.append(f"Dashboard Agent failed: {exc}")

    answer_parts: list[str] = []

    if log_result:
        answer_parts.append(log_result.answer)
    
    if dashboard_result:
        answer_parts.append(dashboard_result.answer)

    if errors:
        answer_parts.append("Some agents failed: " + " | ".join(errors))
    
    if not answer_parts:
        answer_parts.append("I could not complete the multi-agent analysis.")

    return {
        **state,
        "answer": " ".join(answer_parts),
        "evidence": log_result.evidence if log_result else [],
        "aggregations": log_result.aggregations if log_result else [],
        "dashboard": dashboard_result.dashboard if dashboard_result else None,
        "sources": [],
        "used_context": False,
        "error": " | ".join(errors) if errors else "",
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
    graph.add_node("multi_agent", multi_agent)
    graph.add_node("unsupported_agent", unsupported_agent)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "rag_agent": "rag_agent",
            "log_agent": "log_agent",
            "dashboard_agent": "dashboard_agent",
            "multi_agent": "multi_agent",
            "unsupported_agent": "unsupported_agent",
        },
    )

    graph.add_edge("rag_agent", END)
    graph.add_edge("log_agent", END)
    graph.add_edge("dashboard_agent", END)
    graph.add_edge("multi_agent", END)
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
