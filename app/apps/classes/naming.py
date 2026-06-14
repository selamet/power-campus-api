"""Helpers for class display names and level codes."""


def level_code(level: str) -> str:
    """Just the level code, dropping the description: "A1 — Başlangıç" -> "A1"."""
    return (level or "").split("—")[0].strip()


def class_display_name(level: str, section: int) -> str:
    """Human-friendly class label, e.g. ``A1/1``."""
    return f"{level_code(level)}/{section}"
