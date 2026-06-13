"""Playful Turkish term names, used when staff create a term without one."""

import random

_ADJECTIVES = (
    "Neşeli",
    "Cesur",
    "Zarif",
    "Bilge",
    "Çevik",
    "Işıltılı",
    "Meraklı",
    "Sakin",
    "Coşkulu",
    "Görkemli",
    "Şirin",
    "Atılgan",
)
_NOUNS = (
    "Lale",
    "Kanguru",
    "Pusula",
    "Fener",
    "Yelken",
    "Karahindiba",
    "Ahtapot",
    "Kumru",
    "Zümrüt",
    "Çınar",
    "Penguen",
    "Şimşek",
)


def playful_name(year: int) -> str:
    """A fun, human-friendly label like ``2026 · Neşeli Lale``."""
    return f"{year} · {random.choice(_ADJECTIVES)} {random.choice(_NOUNS)}"
