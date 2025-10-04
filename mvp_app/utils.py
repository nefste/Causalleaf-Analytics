"""Utility helpers for formatting and exports."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
import plotly.graph_objects as go


@dataclass
class SeededRNG:
    seed: int

    def generator(self) -> np.random.Generator:
        return np.random.default_rng(self.seed)


def format_percentage(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"


def format_number(value: float, digits: int = 0) -> str:
    formatted = f"{value:,.{digits}f}"
    return formatted.replace(",", " ")


def figure_to_svg_bytes(fig: go.Figure) -> bytes:
    fig.kaleido.scope.chromium_args = (
        "--headless",
        "--no-sandbox",
        "--single-process",
        "--disable-gpu"
    )
    buffer = fig.to_image(format="svg")
    if isinstance(buffer, bytes):
        return buffer
    if isinstance(buffer, str):
        return buffer.encode("utf-8")
    if isinstance(buffer, BytesIO):
        return buffer.getvalue()
    raise TypeError("Unsupported buffer type returned by plotly")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "SeededRNG",
    "format_percentage",
    "format_number",
    "figure_to_svg_bytes",
    "safe_float",
]
