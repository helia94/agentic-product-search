"""Agent package initialization."""

try:
    from .graph import graph
    __all__ = ["graph"]
except Exception:  # pragma: no cover - optional graph import
    __all__ = []
