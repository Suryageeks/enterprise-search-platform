from __future__ import annotations

from typing import Any


from app.client.opensearch_client import opensearch_log_client
from app.schemas.dashboard import (
    DashboardSpec,
    DashboardWidget,
    DashboardWidgetData,
    ExecutedDashboard,
    ExecutedDashboardWidget,
)

class DashboardExecutorService:
    async def execute_dashboard(self, dashboard: DashboardSpec) -> ExecutedDashboard:
        executed_widgets: list[ExecutedDashboardWidget] = []

        for widget in dashboard.widgets:
            data = await self.execute_widget(widget)

            executed_widgets.append(
                ExecutedDashboardWidget(
                    **widget.model_dump(),
                    data=data
                )
            )
        
        return ExecutedDashboard(
            title=dashboard.title,
            description=dashboard.description,
            time_range=dashboard.time_range,
            widgets=executed_widgets
        )
    
    async def execute_widget(self, widget: DashboardWidget) -> DashboardWidgetData:
        aggregation = widget.query.aggregation
        aggregation_type = aggregation.get("type")

        if aggregation_type == "count":
            return await self.execute_count(widget)

        if aggregation_type == "terms":
            return await self.execute_terms(widget)

        if aggregation_type == "date_histogram":
            return await self.execute_date_histogram(widget)

        if aggregation_type in {"avg", "max", "min", "sum"}:
            return await self.execute_metric(widget)

        if aggregation_type == "top_hits":
            return await self.execute_top_hits(widget)

        return DashboardWidgetData()

    async def execute_count(self, widget: DashboardWidget) -> DashboardWidgetData:
        body = {
            "size": 0,
            "query": self.build_filter_query(widget.query.filters)
        }
        
        response = await opensearch_log_client.client.search(
            index=widget.query.index,
            body=body
        )

        count = response.get("hits", {}).get("total", {}).get("value", 0)

        return DashboardWidgetData(
            labels=["count"],
            values=[count]
        )
    
    async def execute_terms(self, widget: DashboardWidget) -> DashboardWidgetData:
        aggregation = widget.query.aggregation
        field = aggregation["field"]
        size = aggregation.get("size", 10)

        body = {
            "size": 0,
            "query": self.build_filter_query(widget.query.filters),
            "aggs": {
                "result": {
                    "terms": {
                        "field": field,
                        "size": size,
                    }
                }
            },
        }

        response = await opensearch_log_client.client.search(
            index=widget.query.index,
            body=body,
        )

        buckets = response.get("aggregations", {}).get("result", {}).get("buckets", [])

        return DashboardWidgetData(
            labels=[str(bucket.get("key")) for bucket in buckets],
            values=[bucket.get("doc_count", 0) for bucket in buckets],
        )

    async def execute_date_histogram(self, widget: DashboardWidget) -> DashboardWidgetData:
        aggregation = widget.query.aggregation
        field = aggregation.get("field", "timestamp")
        interval = aggregation.get("interval", "5m")

        body = {
            "size": 0,
            "query": self.build_filter_query(widget.query.filters),
            "aggs": {
                "result": {
                    "date_histogram": {
                        "field": field,
                        "fixed_interval": interval,
                    }
                }
            },
        }

        response = await opensearch_log_client.client.search(
            index=widget.query.index,
            body=body,
        )

        buckets = response.get("aggregations", {}).get("result", {}).get("buckets", [])

        return DashboardWidgetData(
            labels=[bucket.get("key_as_string") for bucket in buckets],
            values=[bucket.get("doc_count", 0) for bucket in buckets],
        )

    async def execute_metric(self, widget: DashboardWidget) -> DashboardWidgetData:
        aggregation = widget.query.aggregation
        aggregation_type = aggregation["type"]
        field = aggregation["field"]

        body = {
            "size": 0,
            "query": self.build_filter_query(widget.query.filters),
            "aggs": {
                "result": {
                    aggregation_type: {
                        "field": field,
                    }
                }
            },
        }

        response = await opensearch_log_client.client.search(
            index=widget.query.index,
            body=body,
        )

        value = response.get("aggregations", {}).get("result", {}).get("value")

        return DashboardWidgetData(
            labels=[aggregation_type],
            values=[value or 0],
        )

    async def execute_top_hits(self, widget: DashboardWidget) -> DashboardWidgetData:
        aggregation = widget.query.aggregation
        size = aggregation.get("size", 20)
        sort_config = aggregation.get("sort", [{"timestamp": "desc"}])

        sort = []
        for item in sort_config:
            for field, direction in item.items():
                sort.append({field: {"order": direction}})

        body = {
            "size": size,
            "query": self.build_filter_query(widget.query.filters),
            "sort": sort,
        }

        response = await opensearch_log_client.client.search(
            index=widget.query.index,
            body=body,
        )

        hits = response.get("hits", {}).get("hits", [])

        rows = [
            hit.get("_source", {})
            for hit in hits
        ]

        return DashboardWidgetData(
            rows=rows,
        )

    def build_filter_query(self, filters: dict[str, Any]) -> dict[str, Any]:
        if not filters:
            return {"match_all": {}}

        clauses: list[dict[str, Any]] = []

        for field, value in filters.items():
            if isinstance(value, dict):
                range_body: dict[str, Any] = {}

                if "gte" in value:
                    range_body["gte"] = value["gte"]

                if "lte" in value:
                    range_body["lte"] = value["lte"]

                if "gt" in value:
                    range_body["gt"] = value["gt"]

                if "lt" in value:
                    range_body["lt"] = value["lt"]

                clauses.append(
                    {
                        "range": {
                            field: range_body,
                        }
                    }
                )
            else:
                clauses.append(
                    {
                        "term": {
                            field: value,
                        }
                    }
                )

        return {
            "bool": {
                "filter": clauses,
            }
        }
    

dashboard_executor_service = DashboardExecutorService()
            
        

