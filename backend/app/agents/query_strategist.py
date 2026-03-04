"""
Query Strategist Agent
Expands a user's research topic into three targeted sub-queries using GPT-4
via LangGraph for orchestration.
"""
from __future__ import annotations

import json
from typing import TypedDict, List

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.config import settings

log = structlog.get_logger()

SYSTEM_PROMPT = """You are an expert academic research strategist. Given a research topic,
generate exactly 3 targeted search queries that together provide comprehensive coverage of the
topic. The queries should:
1. Cover the core subject area with precise technical terminology
2. Explore a related application or domain variant
3. Target recent advances, surveys, or comparative studies

Return ONLY a JSON array of 3 strings. No explanation, no markdown, no extra text.
Example output: ["query one", "query two", "query three"]"""


class QueryState(TypedDict):
    topic: str
    sub_queries: List[str]


def expand_queries(state: QueryState) -> QueryState:
    """LLM node: expand topic into sub-queries."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Research topic: {state['topic']}"),
    ]
    response = llm.invoke(messages)
    raw = response.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    queries: List[str] = json.loads(raw.strip())
    if not isinstance(queries, list) or len(queries) != 3:
        raise ValueError(f"Expected list of 3 queries, got: {raw}")
    return {**state, "sub_queries": queries}


# Build LangGraph workflow
_builder = StateGraph(QueryState)
_builder.add_node("expand_queries", expand_queries)
_builder.set_entry_point("expand_queries")
_builder.add_edge("expand_queries", END)
query_graph = _builder.compile()


async def run_query_strategist(topic: str) -> List[str]:
    """Run the Query Strategist Agent and return 3 sub-queries."""
    log.info("QueryStrategist: expanding topic", topic=topic)
    result = await query_graph.ainvoke({"topic": topic, "sub_queries": []})
    queries = result["sub_queries"]
    log.info("QueryStrategist: generated queries", queries=queries)
    return queries
