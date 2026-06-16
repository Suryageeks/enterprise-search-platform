from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.schemas.dashboard import (
    DashboardAgentResult,
    DashboardQuery,
    DashboardSpec,
    DashboardWidget,
)
from app.services.dashboard_executor_service import dashboard_executor_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class DashboardAgentService:
    def __init__(self):    
        self.system_prompt = """
                        You generate dashboard JSON specs for operational log analytics.

                        Return ONLY valid JSON.
                        Do not wrap in markdown.
                        Do not explain.

                        The dashboard must be based on OpenSearch index normalized-logs.

                        Supported widget types:
                            - metric
                            - line
                            - bar
                            - pie
                            - table
                            - heatmap

                        Available log fields:
                            - timestamp
                            - service
                            - environment
                            - level
                            - message
                            - traceId
                            - requestId
                            - statusCode
                            - host
                            - endpoint
                            - exceptionType
                            - tags
                            - rawSource
                            - ingestedAt
                            - durationMs
                            - method
                            - userId

                        Return JSON matching this schema:
                        {
                            "title": "string",
                            "description": "string | null",
                            "time_range": {
                                "from": "ISO-8601 string | null",
                                "to": "ISO-8601 string | null"
                            } | null,
                            "widgets": [
                                {
                                "id": "string",
                                "type": "metric | line | bar | pie | table | heatmap",
                                "title": "string",
                                "description": "string | null",
                                "query": {
                                    "index": "normalized-logs",
                                    "filters": {},
                                    "aggregation": {}
                                }
                                }
                            ]
                        }

                        Rules:
                            - Use filters for service, level, statusCode, endpoint, traceId, environment, and time range.
                            - For 5xx use statusCode gte 500 and lte 599.
                            - For 4xx use statusCode gte 400 and lte 499.
                            - For errors use level ERROR unless status code is more specific.
                            - Include 3 to 6 useful widgets for broad dashboard requests.
                            - Include at least one table widget showing recent matching logs.
                            - Use OpenSearch-style aggregation descriptions.
                            - Make widget IDs short and unique.
                    """

    async def generate_dashboard(self, question: str) -> DashboardAgentResult:
        if settings.dashboard_use_gemini:
            try:
                result = await self.generate_with_gemini(question)
            except Exception:
                logger.exception("Gemini dashboard generation failed; falling back to rules")
                result = self.generate_with_rules(question)
        else:
            result = self.generate_with_rules(question)

        executed_dashboard = await dashboard_executor_service.execute_dashboard(
            result.dashboard
        )

        return DashboardAgentResult(
            answer=result.answer,
            dashboard=executed_dashboard
        )

    async def generate_with_gemini(self, question: str) -> DashboardAgentResult:
        prompt_value = f"{self.system_prompt}\n\nUser dashboard request:\n{question}"

        response = await llm_service.ainvoke(prompt_value)
        raw_text = str(response.content).strip()

        data = self.parse_json(raw_text)
        dashboard = DashboardSpec.model_validate(data)

        return DashboardAgentResult(
            answer=f"Generated dashboard spec: {dashboard.title}",
            dashboard=dashboard,
        )
    
    def generate_with_rules(self, question: str) -> DashboardAgentResult:
        normalized = question.lower().strip()

        if "5xx" in normalized:
            dashboard = self.error_status_dashboard(
                title="5xx Error Dashboard",
                status_min=500,
                status_max=599,
            )
        elif "4xx" in normalized:
            dashboard = self.error_status_dashboard(
                title="4xx Error Dashboard",
                status_min=400,
                status_max=499,
            )
        elif "latency" in normalized or "duration" in normalized or "slow" in normalized:
            dashboard = self.latency_dashboard()
        elif "trace" in normalized:
            dashboard = self.trace_dashboard(question)
        elif "service" in normalized and ("error" in normalized or "errors" in normalized):
            dashboard = self.service_error_dashboard()
        elif "endpoint" in normalized:
            dashboard = self.endpoint_dashboard()
        else:
            dashboard = self.general_log_dashboard()

        return DashboardAgentResult(
            answer=f"Generated dashboard spec: {dashboard.title}",
            dashboard=dashboard,
        )

    def error_status_dashboard(
        self,
        *,
        title: str,
        status_min: int,
        status_max: int,
    ) -> DashboardSpec:
        filters = {
            "statusCode": {
                "gte": status_min,
                "lte": status_max,
            }
        }

        return DashboardSpec(
            title=title,
            description=f"Dashboard for HTTP {status_min}-{status_max} responses.",
            widgets=[
                self.metric_widget(
                    "Total matching errors",
                    filters,
                    {"type": "count"},
                ),
                self.line_widget(
                    "Errors over time",
                    filters,
                    {
                        "type": "date_histogram",
                        "field": "timestamp",
                        "interval": "5m",
                        "metric": "count",
                    },
                ),
                self.bar_widget(
                    "Errors by service",
                    filters,
                    {
                        "type": "terms",
                        "field": "service",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.bar_widget(
                    "Errors by endpoint",
                    filters,
                    {
                        "type": "terms",
                        "field": "endpoint",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.table_widget(
                    "Recent matching logs",
                    filters,
                    {
                        "type": "top_hits",
                        "sort": [{"timestamp": "desc"}],
                        "size": 20,
                    },
                ),
            ],
        )

    def service_error_dashboard(self) -> DashboardSpec:
        filters = {
            "level": "ERROR",
        }

        return DashboardSpec(
            title="Service Error Dashboard",
            description="Errors grouped by service, endpoint, and exception type.",
            widgets=[
                self.metric_widget("Total errors", filters, {"type": "count"}),
                self.bar_widget(
                    "Errors by service",
                    filters,
                    {
                        "type": "terms",
                        "field": "service",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.bar_widget(
                    "Errors by exception type",
                    filters,
                    {
                        "type": "terms",
                        "field": "exceptionType",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.line_widget(
                    "Error trend",
                    filters,
                    {
                        "type": "date_histogram",
                        "field": "timestamp",
                        "interval": "5m",
                        "metric": "count",
                    },
                ),
                self.table_widget(
                    "Recent error logs",
                    filters,
                    {
                        "type": "top_hits",
                        "sort": [{"timestamp": "desc"}],
                        "size": 20,
                    },
                ),
            ],
        )

    def latency_dashboard(self) -> DashboardSpec:
        return DashboardSpec(
            title="Latency Dashboard",
            description="Latency and slow request analysis.",
            widgets=[
                self.metric_widget(
                    "Average duration",
                    {},
                    {
                        "type": "avg",
                        "field": "durationMs",
                    },
                ),
                self.metric_widget(
                    "Max duration",
                    {},
                    {
                        "type": "max",
                        "field": "durationMs",
                    },
                ),
                self.line_widget(
                    "Average latency over time",
                    {},
                    {
                        "type": "date_histogram",
                        "field": "timestamp",
                        "interval": "5m",
                        "metric": {
                            "type": "avg",
                            "field": "durationMs",
                        },
                    },
                ),
                self.bar_widget(
                    "Slow endpoints",
                    {},
                    {
                        "type": "terms",
                        "field": "endpoint",
                        "metric": {
                            "type": "avg",
                            "field": "durationMs",
                        },
                        "size": 10,
                    },
                ),
                self.table_widget(
                    "Slowest recent requests",
                    {},
                    {
                        "type": "top_hits",
                        "sort": [{"durationMs": "desc"}],
                        "size": 20,
                    },
                ),
            ],
        )

    def trace_dashboard(self, question: str) -> DashboardSpec:
        trace_id = self.extract_trace_id(question)

        filters: dict[str, Any] = {}
        if trace_id:
            filters["traceId"] = trace_id

        return DashboardSpec(
            title="Trace Investigation Dashboard",
            description="Logs and service path for a trace.",
            widgets=[
                self.metric_widget("Trace event count", filters, {"type": "count"}),
                self.bar_widget(
                    "Trace events by service",
                    filters,
                    {
                        "type": "terms",
                        "field": "service",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.line_widget(
                    "Trace events over time",
                    filters,
                    {
                        "type": "date_histogram",
                        "field": "timestamp",
                        "interval": "1m",
                        "metric": "count",
                    },
                ),
                self.table_widget(
                    "Trace log timeline",
                    filters,
                    {
                        "type": "top_hits",
                        "sort": [{"timestamp": "asc"}],
                        "size": 50,
                    },
                ),
            ],
        )

    def endpoint_dashboard(self) -> DashboardSpec:
        return DashboardSpec(
            title="Endpoint Health Dashboard",
            description="Endpoint traffic, errors, and latency.",
            widgets=[
                self.bar_widget(
                    "Requests by endpoint",
                    {},
                    {
                        "type": "terms",
                        "field": "endpoint",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.bar_widget(
                    "5xx by endpoint",
                    {"statusCode": {"gte": 500, "lte": 599}},
                    {
                        "type": "terms",
                        "field": "endpoint",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.bar_widget(
                    "Average latency by endpoint",
                    {},
                    {
                        "type": "terms",
                        "field": "endpoint",
                        "metric": {
                            "type": "avg",
                            "field": "durationMs",
                        },
                        "size": 10,
                    },
                ),
                self.table_widget(
                    "Recent endpoint logs",
                    {},
                    {
                        "type": "top_hits",
                        "sort": [{"timestamp": "desc"}],
                        "size": 20,
                    },
                ),
            ],
        )

    def general_log_dashboard(self) -> DashboardSpec:
        return DashboardSpec(
            title="General Log Intelligence Dashboard",
            description="Overview of services, log levels, status codes, and recent events.",
            widgets=[
                self.metric_widget("Total logs", {}, {"type": "count"}),
                self.bar_widget(
                    "Logs by service",
                    {},
                    {
                        "type": "terms",
                        "field": "service",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.pie_widget(
                    "Logs by level",
                    {},
                    {
                        "type": "terms",
                        "field": "level",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.bar_widget(
                    "Status codes",
                    {},
                    {
                        "type": "terms",
                        "field": "statusCode",
                        "metric": "count",
                        "size": 10,
                    },
                ),
                self.line_widget(
                    "Logs over time",
                    {},
                    {
                        "type": "date_histogram",
                        "field": "timestamp",
                        "interval": "5m",
                        "metric": "count",
                    },
                ),
                self.table_widget(
                    "Recent logs",
                    {},
                    {
                        "type": "top_hits",
                        "sort": [{"timestamp": "desc"}],
                        "size": 20,
                    },
                ),
            ],
        )
    
    def metric_widget(self, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return self.widget(
            widget_type="metric",
            title=title,
            filters=filters,
            aggregation=aggregation
        )

    def line_widget(self, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return self.widget(
            widget_type="line",
            title=title,
            filters=filters,
            aggregation=aggregation
        )
    
    def bar_widget(self, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return self.widget(
            widget_type="bar",
            title=title,
            filters=filters,
            aggregation=aggregation
        )
    
    def pie_widget(self, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return self.widget(
            widget_type="pie",
            title=title,
            filters=filters,
            aggregation=aggregation
        )

    def table_widget(self, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return self.widget(
            widget_type="table",
            title=title,
            filters=filters,
            aggregation=aggregation
        )

    def widget(self, *, widget_type: str, title: str, filters: dict[str, Any], aggregation: dict[str, Any]) -> DashboardWidget:
        return DashboardWidget(
            id=self.new_widget_id(title),
            type=widget_type,
            title=title,
            query=DashboardQuery(
                index=settings.opensearch_index,
                filters=filters,
                aggregation=aggregation
            )
        )
    
    def parse_json(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

        return json.loads(cleaned)

    def extract_trace_id(self, question: str) -> str | None:
        for token in question.split():
            normalized = token.strip(".,;:()[]{}")
            if normalized.startswith("trace-"):
                return normalized
        
        return None

    def new_widget_id(self, title: str) -> str:
        slug = (
            title.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("_", "-")
        )

        return f"{slug[:32]}-{uuid4().hex[:6]}"
    
dashboard_agent_service = DashboardAgentService()
