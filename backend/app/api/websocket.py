"""
WebSocket endpoint for real-time RAG chat.
Users can query their paper collection; the server retrieves relevant papers
from Pinecone and generates a cited response using GPT-4.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.services.pinecone_service import query_papers

log = structlog.get_logger()
router = APIRouter()

CHAT_SYSTEM = """You are a knowledgeable research assistant with access to a curated collection
of academic papers. When answering questions:
1. Base your answers primarily on the provided paper excerpts
2. Cite papers using their IEEE numbers [n] inline
3. Be precise and technical
4. If the provided papers don't fully answer the question, say so clearly
5. Keep responses concise (3-6 sentences) unless more detail is requested"""


async def _rag_response(query: str, namespace: str) -> str:
    """Retrieve relevant papers and generate a cited response."""
    papers = await query_papers(query, namespace, top_k=5)

    context_parts = []
    for p in papers:
        ieee_num = p.get("ieee_number") or "?"
        context_parts.append(
            f"[{ieee_num}] {p.get('title', '')}\n"
            f"  Summary: {p.get('summary', '')}"
        )

    context = "\n\n".join(context_parts) if context_parts else "No relevant papers found."

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )

    response = await llm.ainvoke([
        SystemMessage(content=CHAT_SYSTEM),
        HumanMessage(
            content=f"Relevant papers:\n{context}\n\nUser question: {query}"
        ),
    ])
    return response.content.strip()


@router.websocket("/chat/{survey_id}")
async def websocket_chat(websocket: WebSocket, survey_id: int):
    """WebSocket endpoint for RAG-powered chat over a survey's paper collection."""
    await websocket.accept()
    namespace = f"survey-{survey_id}"
    log.info("WebSocket connected", survey_id=survey_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data: Dict[str, Any] = json.loads(raw)
                query = data.get("message", "").strip()
            except json.JSONDecodeError:
                query = raw.strip()

            if not query:
                await websocket.send_json({"error": "Empty message"})
                continue

            # Send typing indicator
            await websocket.send_json({"type": "typing", "content": ""})

            try:
                answer = await _rag_response(query, namespace)
                await websocket.send_json({
                    "type": "message",
                    "role": "assistant",
                    "content": answer,
                })
            except Exception as exc:
                log.error("WebSocket RAG error", error=str(exc))
                await websocket.send_json({
                    "type": "error",
                    "content": "Failed to generate response. Please try again.",
                })

    except WebSocketDisconnect:
        log.info("WebSocket disconnected", survey_id=survey_id)
