"""
AURA Multi-Model Router
-----------------------
Analyses a user query and routes it to the appropriate local Ollama model:
  - GENERAL  → llama3.1  (everyday college assistant tasks)
  - CODING   → qwen3     (code generation / debugging)
  - REASONING→ llama3.1  (logical / analytical tasks; swap for deepseek-r1 if pulled)

The router is intentionally keyword-driven and fast (no LLM call needed) so it
adds zero latency. It can be replaced with a small classifier later.
"""

from __future__ import annotations
import re
from enum import Enum
from app.database.config import settings


class TaskType(str, Enum):
    GENERAL = "general"
    CODING = "coding"
    REASONING = "reasoning"


# ── Keyword heuristics ──────────────────────────────────────────────────────
_CODING_PATTERNS = re.compile(
    r"\b(code|program|function|class|debug|error|exception|algorithm|"
    r"script|implement|compile|syntax|python|javascript|java|c\+\+|sql|"
    r"api|library|import|variable|loop|array|dict|object|bug|fix|refactor)\b",
    re.IGNORECASE,
)

_REASONING_PATTERNS = re.compile(
    r"\b(explain|analyse|analyze|compare|evaluate|reason|logic|pros|cons|"
    r"difference|calculate|solve|proof|derive|critical|think|strategy|"
    r"should i|what is better|why|how does)\b",
    re.IGNORECASE,
)


class ModelRouter:
    """
    Routes a user query to the correct Ollama model name.

    Usage:
        router = ModelRouter()
        model_name, task_type = router.route("write a python function to sort a list")
        # → ("qwen3", TaskType.CODING)
    """

    def __init__(self) -> None:
        self._model_map: dict[TaskType, str] = {
            TaskType.GENERAL: settings.GENERAL_MODEL,
            TaskType.CODING: settings.CODING_MODEL,
            TaskType.REASONING: settings.REASONING_MODEL,
        }

    def classify(self, query: str) -> TaskType:
        """Classify query into a task type using lightweight regex heuristics."""
        if _CODING_PATTERNS.search(query):
            return TaskType.CODING
        if _REASONING_PATTERNS.search(query):
            return TaskType.REASONING
        return TaskType.GENERAL

    def route(self, query: str) -> tuple[str, TaskType]:
        """Return (model_name, task_type) for the given query string."""
        task_type = self.classify(query)
        model_name = self._model_map[task_type]
        return model_name, task_type

    def get_model(self, task_type: TaskType) -> str:
        """Directly look up a model by task type."""
        return self._model_map[task_type]


# Singleton — import this everywhere instead of instantiating
model_router = ModelRouter()
