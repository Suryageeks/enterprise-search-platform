from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.schemas.logs import ParsedLogQuery

class LogQueryParser:
    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=settings.chat_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            max_output_tokens=settings.max_output_tokens
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                        You convert natural language log questions into strict JSON filters.

                        Return ONLY valid JSON.
                        Do not wrap in markdown.
                        Do not explain.

                        Schema:
                        {
                            "service": string | null,
                            "environment": string | null,
                            "level": "INFO" | "WARN" | "ERROR" | "DEBUG" | null,
                            "trace_id": string | null,
                            "request_id": string | null,
                            "status_code": number | null,
                            "status_code_min": number | null,
                            "status_code_max": number | null,
                            "endpoint": string | null,
                            "exception_type": string | null,
                            "time_range": {
                                "from": ISO-8601 string | null,
                                "to": ISO-8601 string | null
                            } | null,
                            "keywords": string[],
                            "size": number
                        }

                        Rules:
                            - If user says 5xx, use status_code_min=500 and status_code_max=599.
                            - If user says 4xx, use status_code_min=400 and status_code_max=499.
                            - If user says errors, set level="ERROR" unless a more specific meaning is clear.
                            - If user asks for trace, extract trace_id if present.
                            - If user asks for request id, extract request_id if present.
                            - If user mentions service name like payment, orders, catalog, gateway, set service.
                            - If unsure, put remaining important search words in keywords.
                            - size must be between 1 and 100.
                            - Use the current time and timezone for relative time.
                    """,
                ),
                (
                    "human",
                    """
                        Current time: {current_time}
                        Timezone: {timezone}

                        User question:
                        {question}
                    """,
                ),
            ]
        )

    async def parse(self, question: str, size: int = 10) -> ParsedLogQuery:
        now = datetime.now(ZoneInfo(settings.app_timezone)).isoformat()

        prompt_value = self.prompt.invoke(
            {
                "current_time": now,
                "timezone": settings.app_timezone,
                "question": question
            }
        )

        response = await self.llm.ainvoke(prompt_value)
        raw_text = str(response.content).strip()

        data = self._parse_json(raw_text)

        if not data.get("size"):
            data["size"] = size
        
        return ParsedLogQuery.model_validate(data)

    def _parse_json(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

        return json.loads(cleaned)

log_query_parser = LogQueryParser()




        
