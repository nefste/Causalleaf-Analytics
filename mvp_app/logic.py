"""Ampel logic and decision heuristics."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Tuple

import pandas as pd


AMPel_COLORS = {
    "GRÜN": "#2e7d32",
    "GELB": "#f9a825",
    "ROT": "#c62828",
    "BLAU": "#1565c0",
}


@dataclass
class AmpelThresholds:
    gruen: float = 0.05
    gelb: float = 0.15

    def as_dict(self) -> Dict[str, float]:
        return {"gruen": self.gruen, "gelb": self.gelb}


def ampel_status(norm_gap: float, thresholds: AmpelThresholds) -> Tuple[str, str]:
    """Return (label, color) for given normalised gap."""

    if norm_gap >= thresholds.gelb:
        return "ROT", AMPel_COLORS["ROT"]
    if norm_gap >= thresholds.gruen:
        return "GELB", AMPel_COLORS["GELB"]
    if norm_gap <= -thresholds.gelb:
        return "ROT", AMPel_COLORS["ROT"]
    if norm_gap <= -thresholds.gruen:
        return "BLAU", AMPel_COLORS["BLAU"]
    return "GRÜN", AMPel_COLORS["GRÜN"]


def format_recommendation(
    resource: str,
    gap: float,
    capacity: float,
    nurse_ratio: float,
    thresholds: AmpelThresholds,
) -> str:
    """Generate heuristic recommendations based on gap."""

    if capacity <= 0:
        return "Kapazität unbekannt – manuelle Prüfung erforderlich."

    norm_gap = gap / capacity
    status, _ = ampel_status(norm_gap, thresholds)

    shortage = gap > 0
    magnitude = abs(norm_gap)

    if status == "GRÜN":
        return "Keine Maßnahmen nötig – innerhalb des Puffers."

    factor = 1.0
    if status == "GELB":
        factor = 0.35

    op_shift = math.ceil(max(0.0, gap) * factor / max(capacity, 1) * 100)
    open_beds = math.ceil(max(0.0, gap) * factor / 2)
    staff_reassign = math.ceil(max(0.0, gap) * factor / max(nurse_ratio, 1e-6))

    if not shortage:
        # Overcapacity suggestions
        release = math.ceil(abs(gap) * factor / 2)
        return (
            f"Überkapazität nutzen: {release} Termine vorziehen, Reservepersonal nur bei Bedarf einplanen,"
            " Betten flexibel schließen."
        )

    suggestions = []
    if resource in {"OP", "Sprechstunden"} and op_shift > 0:
        suggestions.append(f"OP-Programm um {op_shift}% glätten")
    if resource in {"Betten", "Notfall"} and open_beds > 0:
        suggestions.append(f"{open_beds} Betten temporär öffnen")
    if staff_reassign > 0:
        suggestions.append(f"{staff_reassign} Pflege-Schichten umplanen")

    if not suggestions:
        base = max(1, math.ceil(magnitude * 10))
        suggestions.append(f"Kapazität um {base} Einheiten anpassen")

    return ", ".join(suggestions)


def describe_cell(row: pd.Series, thresholds: AmpelThresholds, nurse_ratio: float) -> Dict[str, str | float]:
    gap = float(row["gap"])
    capacity = float(row["capacity_sum"])
    norm_gap = gap / capacity if capacity else 0.0
    status, color = ampel_status(norm_gap, thresholds)
    recommendation = format_recommendation(
        row["resource"], gap, capacity, nurse_ratio, thresholds
    )
    return {
        "resource": row["resource"],
        "kw": int(row["week"]),
        "status": status,
        "farbe": color,
        "gap": gap,
        "norm_gap": norm_gap,
        "empfehlung": recommendation,
    }


__all__ = ["AmpelThresholds", "ampel_status", "format_recommendation", "describe_cell", "AMPel_COLORS"]
