import logging
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.core.config import settings

logger = logging.getLogger(__name__)

class LlmService:
    def __init__(self) -> None:
        self.gemini = None

        if settings.google_api_key:
            self.gemini = ChatGoogleGenerativeAI(
                model=settings.chat_model,
                google_api_key=settings.google_api_key,
                temperature=settings.temperature,
                max_output_tokens=settings.max_output_tokens,
            )

        self.ollama = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_host,
            temperature=settings.temperature,
        )

    async def ainvoke(self, messages: list[BaseMessage] | Any) -> BaseMessage:
        if self.gemini is None:
            return await self.ollama.ainvoke(messages)

        try:
            return await self.gemini.ainvoke(messages)
        except Exception as exc:
            if not self._should_fallback(exc):
                raise
            logger.warning("Gemini failed/rate-limited. Falling back to Ollama: %s", exc)

            if not settings.enable_ollama_fallback:
                raise
            return await self.ollama.ainvoke(messages)

    async def ainvoke_with_tools(
        self,
        tools: list[Any],
        messages: list[BaseMessage],
    ) -> BaseMessage:
        """
        Use Gemini as the primary tool-calling model and Ollama as fallback.
        This requires the configured Ollama model to support tool calls.
        """
        ollama_with_tools = self.ollama.bind_tools(tools)

        if self.gemini is None:
            return await ollama_with_tools.ainvoke(messages)

        try:
            gemini_with_tools = self.gemini.bind_tools(tools)
            return await gemini_with_tools.ainvoke(messages)
        except Exception as exc:
            if not self._should_fallback(exc):
                raise

            logger.warning(
                "Gemini tool call failed/rate-limited. Falling back to Ollama: %s",
                exc,
            )

            if not settings.enable_ollama_fallback:
                raise

            return await ollama_with_tools.ainvoke(messages)
    
    def _should_fallback(self, exc: Exception) -> bool:
        message = str(exc).lower()

        fallback_markers = [
            "429",
            "rate limit",
            "ratelimit",
            "quota",
            "resource exhausted",
            "too many requests",
            "temporarily unavailable",
            "service unavailable",
        ]

        return any(marker in message for marker in fallback_markers)

llm_service = LlmService()
