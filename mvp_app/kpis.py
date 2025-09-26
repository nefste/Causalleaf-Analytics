"""KPI calculations and driver summaries."""
from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

try:
    from .logic import AmpelThresholds
except ImportError:  # pragma: no cover - allow script execution
    from logic import AmpelThresholds


DRIVER_LABELS = {
    "driver_flu_index": "Epidemie/Grippe",
    "driver_weather_risk": "Wetter/Unfälle",
    "driver_event_impact": "Event-Effekte",
    "driver_verweildauer": "Verweildauer",
    "driver_op_zeiten": "OP-Zeiten",
    "driver_nurse_ratio": "Patient-Pflege-Ratio",
    "driver_abwesenheiten": "Abwesenheiten",
    "driver_cluster": "Stations-Cluster",
    "driver_rest": "Sonstige",
}


def compute_kpis(
    df: pd.DataFrame,
    today: date,
    thresholds: AmpelThresholds,
) -> Dict[str, float]:
    """Aggregate KPI metrics for dashboards."""

    df = df.copy()
    df["is_past"] = df["date"].dt.date <= today
    past = df[df["is_past"]]
    if past.empty:
        past = df.head(7)

    current_week = today.isocalendar().week
    week_data = df[df["week"] == current_week]

    observed_mask = week_data["actuals_to_date"].notna()
    actual_sum = week_data.loc[observed_mask, "actuals_to_date"].sum()
    capacity_sum = week_data.loc[observed_mask, "capacity"].sum()
    utilisation = float(actual_sum / capacity_sum) if capacity_sum else 0.0
    utilisation = float(min(1.0, utilisation))

    # MAPE across past weeks grouped by resource
    past_weekly = (
        past.groupby(["week", "resource"])[["actuals", "forecast"]]
        .sum()
        .reset_index()
    )
    if past_weekly.empty:
        mape = 0.0
    else:
        actual = past_weekly["actuals"].replace(0, np.nan)
        forecast = past_weekly["forecast"]
        mape = float((np.abs(actual - forecast) / actual).replace(np.nan, 0).mean())

    # Wartetage proportional zu kumuliertem positiven Gap
    positive_gap = past["gap"].clip(lower=0)
    waiting_days = float(positive_gap.sum())

    # Stornoquote aus Überlastung
    norm_gap_positive = past["norm_gap"].clip(lower=0)
    cancellation_rate = float((0.005 + 0.05 * norm_gap_positive).mean())

    # Pflege-Engpassindikator (0-100)
    nurse_pressure = past[past["resource"] == "Personal"]
    if nurse_pressure.empty:
        engpass_score = 0.0
    else:
        norm = nurse_pressure["norm_gap"].mean()
        engpass_score = float(np.interp(norm, [-0.1, 0.0, 0.3, 0.6], [10, 30, 70, 95]))

    return {
        "Auslastung": utilisation * 100,
        "MAPE": mape * 100,
        "Wartetage": waiting_days,
        "Stornoquote": cancellation_rate * 100,
        "Pflege-Engpass": engpass_score,
    }


def top_drivers_for_date(df: pd.DataFrame, target: date | None = None) -> List[Tuple[str, float]]:
    if target is None:
        target = df["date"].dt.date.min() if df.empty else df["date"].dt.date.max()

    snapshot = df[df["date"].dt.date == target]
    if snapshot.empty:
        distances = (df["date"].dt.date - target).abs()
        nearest_idx = distances.idxmin()
        nearest_date = df.loc[nearest_idx, "date"].date()
        snapshot = df[df["date"].dt.date == nearest_date]

    driver_cols = [col for col in df.columns if col.startswith("driver_")]
    contributions = snapshot.groupby("resource")[driver_cols].sum().sum(axis=0)
    items = [(DRIVER_LABELS.get(k, k), float(v)) for k, v in contributions.items()]
    items.sort(key=lambda item: abs(item[1]), reverse=True)
    return items[:3]


def weekly_sparkline(df: pd.DataFrame, today: date) -> pd.DataFrame:
    """Aggregate weekly actual vs forecast for sparkline plot."""

    past = df[df["date"].dt.date <= today]
    if past.empty:
        past = df.head(30)
    agg = (
        past.groupby("week")[["actuals", "forecast", "capacity"]]
        .sum()
        .reset_index()
        .sort_values("week")
    )
    return agg


__all__ = ["compute_kpis", "top_drivers_for_date", "weekly_sparkline", "DRIVER_LABELS"]
