"""Agent 1: Query Strategist — Expands a research topic into targeted sub-queries."""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.services.llm_service import BaseLLMService

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert academic research strategist. Your role is to take a research topic 
and expand it into exactly 3 targeted sub-queries that will maximize coverage when searching academic databases.

Each sub-query should:
1. Target a different aspect or dimension of the research topic
2. Use precise academic terminology and key phrases
3. Be optimized for academic search engines (Semantic Scholar, arXiv, Crossref)
4. Together, the 3 queries should cover the breadth of the topic

Consider these dimensions when crafting queries:
- Core technical approaches and methods
- Applications and use cases
- Theoretical foundations and surveys

Respond with ONLY valid JSON in this format:
{
    "original_topic": "the user's original topic",
    "sub_queries": [
        {
            "query": "the search query string",
            "rationale": "brief explanation of what aspect this covers",
            "focus": "methods|applications|theory"
        },
        ...
    ],
    "topic_summary": "A one-sentence summary of the research area"
}"""


class QueryStrategistAgent:
    """Expands a research topic into 3 targeted sub-queries using LLM."""

    def __init__(self, llm: BaseLLMService):
        self.llm = llm

    async def expand_query(self, topic: str) -> dict[str, Any]:
        """Take a research topic and generate 3 sub-queries.

        Args:
            topic: The user's research topic.

        Returns:
            Dictionary with original_topic, sub_queries list, and topic_summary.
        """
        logger.info("query_strategist_start", topic=topic)

        prompt = f"""Research Topic: {topic}

Generate exactly 3 targeted academic search queries to comprehensively survey this topic.
Remember to respond with ONLY valid JSON."""

        try:
            response = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.4,
            )

            result = json.loads(response)

            # Validate structure
            if "sub_queries" not in result or len(result["sub_queries"]) != 3:
                raise ValueError("Expected exactly 3 sub_queries")

            logger.info(
                "query_strategist_complete",
                topic=topic,
                queries=[q["query"] for q in result["sub_queries"]],
            )
            return result

        except json.JSONDecodeError:
            logger.error("query_strategist_json_error", response=response[:200])
            # Fallback: create basic queries from the topic
            return self._fallback_queries(topic)
        except Exception as e:
            logger.error("query_strategist_error", error=str(e))
            return self._fallback_queries(topic)

    def _fallback_queries(self, topic: str) -> dict[str, Any]:
        """Generate fallback queries when LLM fails."""
        return {
            "original_topic": topic,
            "sub_queries": [
                {
                    "query": f"{topic} survey methods approaches",
                    "rationale": "Core methods and approaches",
                    "focus": "methods",
                },
                {
                    "query": f"{topic} applications real-world",
                    "rationale": "Applications and use cases",
                    "focus": "applications",
                },
                {
                    "query": f"{topic} theoretical foundations analysis",
                    "rationale": "Theoretical foundations",
                    "focus": "theory",
                },
            ],
            "topic_summary": f"A comprehensive survey of {topic}",
        }
