from __future__ import annotations

from langchain_core.tools import tool

from app.schemas.execution import ToolErrorCode
from app.services.dashboard_agent_service import dashboard_agent_service
from app.services.tool_result_service import execute_tool, tool_error

@tool
async def generate_dashboard_tool(query: str) -> str:
    """
    Generate and execute a log analytics dashboard.

    Use this when the user asks to create, generate, visualize, plot, graph,
    chart, or build a dashboard/report for logs, errors, services, endpoints,
    traces, latency, status codes, or exceptions.
    """

    if not query.strip():
        return tool_error(
            tool="generate_dashboard_tool",
            code=ToolErrorCode.INVALID_TOOL_INPUT,
            message="Dashboard query cannot be empty",
        )

    async def operation() -> dict:

        result = await dashboard_agent_service.generate_dashboard(
            question=query,
        )

        dashboard = result.dashboard

        return {
            "answer": result.answer,
            "dashboard": dashboard.model_dump(mode="json") if dashboard else None,
        }

    return await execute_tool(
        tool="generate_dashboard_tool",
        operation=operation,
        failure_code=ToolErrorCode.DASHBOARD_EXECUTION_FAILED,
        failure_message="Unable to generate the dashboard",
    )
