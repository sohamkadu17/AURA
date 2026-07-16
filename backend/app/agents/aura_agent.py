"""
AURA LangChain Agent
---------------------
Builds a conversational chain using LangChain LCEL (pipe syntax).

Pipeline per request:
  history + user message
       ↓
  ChatPromptTemplate  (injects AURA system prompt + conversation history)
       ↓
  ChatOllama          (routed model via ModelRouter — llama3.1 / qwen3)
       ↓
  StrOutputParser     (clean text response)

Supports both .invoke() for normal responses and .stream() for
streaming (used by the SSE endpoint).
"""
from __future__ import annotations

import logging
from typing import Iterator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from app.database.config import settings
from app.services.model_router import model_router, TaskType

logger = logging.getLogger(__name__)


# ── AURA System Prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are AURA (Autonomous University Response Assistant), a personal AI assistant "
    "designed specifically to help a college student manage their academic life.\n\n"
    "Your capabilities:\n"
    "- Tracking assignments, deadlines, and exams\n"
    "- Organizing a daily study schedule\n"
    "- Answering questions from uploaded college notes\n"
    "- Creating reminders and tasks\n"
    "- Providing study recommendations\n\n"
    "Personality: Friendly, concise, proactive. Always focused on helping the student succeed. "
    "CRITICAL: If the user wants to set an alarm or reminder, you MUST output a special command block exactly like this: "
    "[ALARM: YYYY-MM-DD HH:MM | Your reminder message]. "
    "Example: [ALARM: 2026-07-15 19:45 | DBMS assignment deadline]. "
    "You MUST use 24-hour format for the time. You MUST include this block at the end of your response to actually schedule the alarm. "
    "If you don't know something from the notes, say so honestly.\n\n"
    "The current system date and time is: {current_time}. "
    "All time calculations and alarms MUST be relative to this time."
)

# ── Prompt Template ────────────────────────────────────────────────────────────
# MessagesPlaceholder will be filled with the conversation history list.
_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

_OUTPUT_PARSER = StrOutputParser()


# ── Chain Factory ──────────────────────────────────────────────────────────────
def _build_chain(model_name: str):
    """Build and return a LangChain LCEL chain for the given Ollama model."""
    llm = ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.7,
    )
    # LCEL pipe: prompt → llm → parser
    return _PROMPT | llm | _OUTPUT_PARSER


# ── Public Interface ───────────────────────────────────────────────────────────
def get_response(user_message: str, history: list[dict]) -> tuple[str, str, str]:
    """
    Get a synchronous response from the routed model.

    Args:
        user_message: The latest message from the user.
        history:      List of {"role": "user"|"assistant", "content": str} dicts
                      representing the conversation so far (short-term memory).

    Returns:
        (response_text, model_name, task_type_str)
    """
    model_name, task_type = model_router.route(user_message)

    # Convert history dicts → LangChain message objects
    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            lc_history.append(SystemMessage(content=msg["content"]))

    chain = _build_chain(model_name)
    from datetime import datetime

    try:
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p (24-hour format: %H:%M)")
        response = chain.invoke({"input": user_message, "history": lc_history, "current_time": current_time})
        logger.info(
            f"[AURA] model={model_name} | task={task_type.value} | "
            f"~{len(response.split())} words"
        )
        return response, model_name, task_type.value
    except Exception as e:
        logger.error(f"[AURA] Ollama error: {e}")
        return (
            "⚠️ AURA could not reach the AI model. "
            "Please ensure Ollama is running: `ollama serve`",
            model_name,
            task_type.value,
        )


def stream_response(user_message: str, history: list[dict]) -> Iterator[str]:
    """
    Stream tokens from the model one-by-one (for SSE / streaming endpoints).

    Yields:
        str token chunks as they arrive from Ollama.
    """
    model_name, task_type = model_router.route(user_message)

    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    chain = _build_chain(model_name)
    from datetime import datetime

    try:
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p (24-hour format: %H:%M)")
        for chunk in chain.stream({"input": user_message, "history": lc_history, "current_time": current_time}):
            yield chunk
    except Exception as e:
        logger.error(f"[AURA] Stream error: {e}")
        yield "⚠️ Streaming error. Check that Ollama is running."

