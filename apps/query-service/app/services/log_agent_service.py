from __future__ import annotations

from typing import Any

from app.client.opensearch_client import opensearch_log_client
from app.schemas.logs import LogAgentResult, LogAggregation, LogEvidence, ParsedLogQuery
from app.services.log_query_parser import log_query_parser


class LogAgentService:
    async def answer_log_question(self, question: str, size: int = 10) -> LogAgentResult:

        parsed_query = await log_query_parser.parse(
            question=question, 
            size=size
        )

        response = await opensearch_log_client.search_logs(
            parsed_query=parsed_query,
        )

        evidence = self.build_evidence(response)
        aggregations = self.build_aggregations(response)

        answer = self.build_answer(
            question=question,
            parsed_query=parsed_query,
            evidence=evidence,
            aggregations=aggregations,
        )

        return LogAgentResult(
            answer=answer,
            evidence=evidence,
            aggregations=aggregations,
        )

    def build_evidence(self, response: dict[str, Any]) -> list[LogEvidence]:
        hits = response.get("hits", {}).get("hits", [])
        evidence: list[LogEvidence] = []

        for hit in hits:
            source = hit.get("_source", {})

            evidence.append(
                LogEvidence(
                    timestamp=source.get("timestamp"),
                    service=source.get("service"),
                    level=source.get("level"),
                    message=source.get("message"),
                    trace_id=source.get("traceId"),
                    request_id=source.get("requestId"),
                    status_code=source.get("statusCode"),
                    endpoint=source.get("endpoint"),
                    raw=source,
                )
            )

        return evidence
    
    def build_aggregations(self, response: dict[str, Any]) -> list[LogAggregation]:
        raw_aggs = response.get("aggregations", {})

        aggregations: list[LogAggregation] = []

        for name, agg in raw_aggs.items():
            buckets = agg.get("buckets", [])

            aggregations.append(
                LogAggregation(
                    name=name,
                    buckets=buckets,
                )
            )

        return aggregations
    
    def build_answer(
        self, 
        *, 
        question: str, 
        parsed_query: ParsedLogQuery,
        evidence: list[LogEvidence], 
        aggregations: list[LogAggregation]
    ) -> str:
        if not evidence:
            return "I could not find matching logs in OpenSearch."

        services = sorted({item.service for item in evidence if item.service})
        levels = sorted({item.level for item in evidence if item.level})

        filters_used: list[str] = []

        total: int = len(evidence)

        if parsed_query.service:
            filters_used.append(f"service={parsed_query.service}")

        if parsed_query.level:
            filters_used.append(f"level={parsed_query.level}")

        if parsed_query.status_code:
            filters_used.append(f"statusCode={parsed_query.status_code}")

        if parsed_query.status_code_min or parsed_query.status_code_max:
            filters_used.append(
                f"statusCode={parsed_query.status_code_min or '*'}-{parsed_query.status_code_max or '*'}"
            )

        if parsed_query.trace_id:
            filters_used.append(f"traceId={parsed_query.trace_id}")

        filter_summary = ", ".join(filters_used) if filters_used else "Keyword search"

        return (
            f"Found {total} matching log events using {filter_summary}. "
            f"Services: {', '.join(services) or 'unknown'}. "
            f"Levels: {', '.join(levels) or 'unknown'}."
        )

log_agent_service = LogAgentService()

    
