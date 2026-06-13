from __future__ import annotations

from typing import Any

from opensearchpy import AsyncOpenSearch

from app.core.config import settings
from app.schemas.logs import ParsedLogQuery

class OpenSearchLogClient:
    def __init__(self) -> None:
        http_auth = None

        if settings.opensearch_username and settings.opensearch_password:
            http_auth = (settings.opensearch_username, settings.opensearch_password)
        
        self.client = AsyncOpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=http_auth,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
        )
    
    async def search_logs(self, *, parsed_query: ParsedLogQuery) -> dict[str, Any]:
        body = {
            "size": parsed_query.size,
            "sort": [
                {
                    "timestamp": {
                        "order": "desc"
                    }
                }
            ],
            "query": self.build_query(parsed_query),
            "aggs": {
                "by_service": {
                    "terms": {
                        "field": "service",
                        "size": 10
                    }
                },
                "by_level": {
                    "terms": {
                        "field": "level",
                        "size": 10
                    }
                },
                "top_status_codes": {
                    "terms": {
                        "field": "statusCode",
                        "size": 10
                    }
                },
            }
        }

        return await self.client.search(
            index=settings.opensearch_index,
            body=body,
        )

    def build_query(self, parsed_query: ParsedLogQuery) -> dict[str, Any]:
        filters: list[dict[str, Any]] = []
        must: list[dict[str, Any]] = []

        if parsed_query.service:
            filters.append({"term": {"service": parsed_query.service}})

        if parsed_query.environment:
            filters.append({"term": {"environment": parsed_query.environment}})

        if parsed_query.level:
            filters.append({"term": {"level": parsed_query.level.upper()}})

        if parsed_query.trace_id:
            filters.append({"term": {"traceId": parsed_query.trace_id}})

        if parsed_query.request_id:
            filters.append({"term": {"requestId": parsed_query.request_id}})

        if parsed_query.status_code is not None:
            filters.append({"term": {"statusCode": parsed_query.status_code}})

        if parsed_query.status_code_min is not None or parsed_query.status_code_max is not None:
            range_body: dict[str, Any] = {}

            if parsed_query.status_code_min is not None:
                range_body["gte"] = parsed_query.status_code_min

            if parsed_query.status_code_max is not None:
                range_body["lte"] = parsed_query.status_code_max

            filters.append({"range": {"statusCode": range_body}})

        if parsed_query.endpoint:
            filters.append({"term": {"endpoint": parsed_query.endpoint}})

        if parsed_query.exception_type:
            filters.append({"term": {"exceptionType": parsed_query.exception_type}})

        if parsed_query.time_range:
            time_body: dict[str, Any] = {}

            if parsed_query.time_range.from_time:
                time_body["gte"] = parsed_query.time_range.from_time

            if parsed_query.time_range.to_time:
                time_body["lte"] = parsed_query.time_range.to_time

            if time_body:
                filters.append({"range": {"timestamp": time_body}})

        if parsed_query.keywords:
            must.append(
                {
                    "multi_match": {
                        "query": " ".join(parsed_query.keywords),
                        "fields": [
                            "message",
                            "service",
                            "level",
                            "traceId",
                            "requestId",
                            "endpoint",
                            "exceptionType",
                        ],
                        "operator": "or",
                    }
                }
            )

        if not filters and not must:
            return {"match_all": {}}

        return {
            "bool": {
                "filter": filters,
                "must": must,
            }
        }

    async def close(self) -> None:
        await self.client.close()

opensearch_log_client = OpenSearchLogClient()
