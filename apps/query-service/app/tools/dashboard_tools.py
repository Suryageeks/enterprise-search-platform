from __future__ import annotations

import json

from langchain_core.tools import tool

from app.services.dashboard_agent_service import dashboard_agent_service

@tool
async def generate_dashboard_tool(query: str) -> str:
    """
    Generate and execute a log analytics dashboard.

    Use this when the user asks to create, generate, visualize, plot, graph,
    chart, or build a dashboard/report for logs, errors, services, endpoints,
    traces, latency, status codes, or exceptions.
    """

    result = await dashboard_agent_service.generate_dashboard(
        question=query,
    )

    dashboard = result.dashboard

    return json.dumps(
        {
            "answer": result.answer,
            "dashboard": dashboard.model_dump(mode="json") if dashboard else None,
        },
        default=str,
    )