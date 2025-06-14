"""Detect macro trend changes from news frequency."""
from __future__ import annotations

from collections import Counter
from typing import List, Dict


def detect_trends(words: List[str]) -> Dict[str, int]:
    """Return simple word frequency counts."""
    counts = Counter(word.lower() for word in words)
    return dict(counts)

