"""Data simulation module for the capacity planning MVP."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd


RESOURCES: Tuple[str, ...] = (
    "Betten",
    "OP",
    "Personal",
    "Sprechstunden",
    "Notfall",
)

RESOURCE_BASELINES: Dict[str, float] = {
    "Betten": 120.0,
    "OP": 75.0,
    "Personal": 90.0,
    "Sprechstunden": 60.0,
    "Notfall": 55.0,
}

RESOURCE_EXTERNAL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Betten": {"flu_index": 0.9, "weather_risk": 0.5, "event_impact": 0.3},
    "OP": {"flu_index": 0.4, "weather_risk": 0.2, "event_impact": 0.5},
    "Personal": {"flu_index": 0.3, "weather_risk": 0.2, "event_impact": 0.4},
    "Sprechstunden": {"flu_index": 0.2, "weather_risk": 0.2, "event_impact": 0.6},
    "Notfall": {"flu_index": 0.7, "weather_risk": 0.8, "event_impact": 0.4},
}

RESOURCE_INTERNAL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Betten": {
        "verweildauer": 0.7,
        "op_zeiten": 0.2,
        "nurse_ratio": 0.4,
        "abwesenheiten": 0.6,
        "cluster": 0.1,
    },
    "OP": {
        "verweildauer": 0.1,
        "op_zeiten": 0.8,
        "nurse_ratio": 0.3,
        "abwesenheiten": 0.4,
        "cluster": 0.2,
    },
    "Personal": {
        "verweildauer": 0.2,
        "op_zeiten": 0.2,
        "nurse_ratio": 0.9,
        "abwesenheiten": 0.7,
        "cluster": 0.3,
    },
    "Sprechstunden": {
        "verweildauer": 0.3,
        "op_zeiten": 0.3,
        "nurse_ratio": 0.4,
        "abwesenheiten": 0.5,
        "cluster": 0.4,
    },
    "Notfall": {
        "verweildauer": 0.4,
        "op_zeiten": 0.2,
        "nurse_ratio": 0.5,
        "abwesenheiten": 0.5,
        "cluster": 0.2,
    },
}

BASE_NURSE_RATIO = 5.0
BASE_ABSENCES = 0.05
BASE_CLUSTER_COUNT = 4


@dataclass
class SimulationConfig:
    """Container for simulation parameters."""

    year: int
    seed: int = 42
    budget_growth: float = 0.03
    verweildauer_delta: float = 0.2
    op_zeiten_delta: float = 5.0
    nurse_ratio: float = BASE_NURSE_RATIO
    abwesenheiten: float = 0.06
    cluster_anzahl: int = BASE_CLUSTER_COUNT
    saisonalitaet_staerke: float = 1.0
    flu_index_staerke: float = 0.8
    weather_risk_staerke: float = 0.6
    datenrhythmus: str = "wöchentlich"
    today: date | None = None

    def resolve_today(self) -> date:
        if self.today is not None:
            return self.today
        current = date.today()
        if current.year == self.year:
            return current
        return date(self.year, 12, 31)


class SimulationResult(pd.DataFrame):
    """Typed DataFrame for simulation output."""

    @property
    def _constructor(self):  # type: ignore[override]
        return SimulationResult


def _date_range_for_year(year: int) -> pd.DatetimeIndex:
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    return pd.date_range(start=start, end=end, freq="D")


def _generate_external_indices(
    dates: Iterable[pd.Timestamp],
    saisonalitaet_staerke: float,
    flu_factor: float,
    weather_factor: float,
    rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    dates = list(dates)
    n = len(dates)
    days_in_year = 366 if dates[0].is_leap_year else 365
    day_of_year = np.array([dt.timetuple().tm_yday for dt in dates], dtype=float)

    # Smooth yearly sinusoidal component for general seasonality
    seasonality_base = np.sin(2 * np.pi * (day_of_year / days_in_year))

    # Flu index: strong peaks in late autumn and winter using Gaussian bumps
    flu_peak_winter = np.exp(-0.5 * ((day_of_year - 15) / 18) ** 2)
    flu_peak_autumn = np.exp(-0.5 * ((day_of_year - 330) / 20) ** 2)
    flu_index = flu_factor * (0.7 * flu_peak_winter + 0.5 * flu_peak_autumn)

    # Weather risk: winter risk (snow/ice) + random cold snaps
    winter_profile = 0.5 * (1 + np.cos(2 * np.pi * (day_of_year - 20) / days_in_year))
    weather_risk = weather_factor * (0.6 * winter_profile + 0.1 * seasonality_base)

    # Event impact: random impulses during holidays/events
    event_impact = np.zeros(n)
    holidays = [
        (1, 1),
        (12, 24),
        (12, 31),
        (4, 1),
        (8, 1),
    ]
    for month, day in holidays:
        mask = [dt.month == month and abs(dt.day - day) <= 2 for dt in dates]
        event_impact += 0.4 * np.array(mask, dtype=float)
    # Additional random impulses (e.g., city marathon, fair)
    impulse_days = rng.choice(n, size=6, replace=False)
    for idx in impulse_days:
        event_impact[idx : idx + 2] += rng.uniform(0.2, 0.5)

    # Seasonality channel for further adjustments
    seasonality = saisonalitaet_staerke * seasonality_base

    return {
        "seasonality": seasonality,
        "flu_index": flu_index,
        "weather_risk": weather_risk,
        "event_impact": event_impact,
    }


def _year_fraction(idx: int, total: int) -> float:
    return idx / max(1, total - 1)


def simulate_year(config: SimulationConfig) -> SimulationResult:
    """Simulate plan, forecast, capacity and drivers for all resources."""

    dates = _date_range_for_year(config.year)
    rng = np.random.default_rng(config.seed)
    todays_date = config.resolve_today()
    external = _generate_external_indices(
        dates,
        config.saisonalitaet_staerke,
        config.flu_index_staerke,
        config.weather_risk_staerke,
        rng,
    )
    total_days = len(dates)

    data_rows = []

    for resource in RESOURCES:
        base = RESOURCE_BASELINES[resource]
        ext_weights = RESOURCE_EXTERNAL_WEIGHTS[resource]
        int_weights = RESOURCE_INTERNAL_WEIGHTS[resource]

        for idx, current_date in enumerate(dates):
            year_progress = _year_fraction(idx, total_days)
            weekday = current_date.weekday()
            weekend_factor = 0.05 if weekday >= 5 else -0.03
            trend_factor = 0.05 * (year_progress - 0.5)  # symmetric around mid-year

            seasonality = external["seasonality"][idx]
            flu_idx = external["flu_index"][idx]
            weather_risk = external["weather_risk"][idx]
            event_impact = external["event_impact"][idx]

            # Plan baseline with growth and seasonality
            plan_base = base * (1 + config.budget_growth)
            plan_modifiers = 1 + 0.25 * seasonality + weekend_factor + trend_factor * 0.3
            plan_value = plan_base * plan_modifiers

            # Internal parameter deltas as percentage adjustments
            verweildauer_pct = int_weights["verweildauer"] * config.verweildauer_delta * 0.02
            op_zeiten_pct = int_weights["op_zeiten"] * (config.op_zeiten_delta / 60.0) * 0.05
            nurse_ratio_pct = int_weights["nurse_ratio"] * (
                (BASE_NURSE_RATIO - config.nurse_ratio) / BASE_NURSE_RATIO
            ) * 0.6
            abwesenheiten_pct = int_weights["abwesenheiten"] * (
                (config.abwesenheiten - BASE_ABSENCES) / max(BASE_ABSENCES, 1e-3)
            ) * 0.4
            cluster_pct = int_weights["cluster"] * (
                (config.cluster_anzahl - BASE_CLUSTER_COUNT) / max(BASE_CLUSTER_COUNT, 1)
            ) * 0.05

            internal_pct = (
                verweildauer_pct
                + op_zeiten_pct
                + nurse_ratio_pct
                + abwesenheiten_pct
                + cluster_pct
            )

            # External factors as percentage adjustments
            external_pct = (
                ext_weights["flu_index"] * flu_idx * 0.4
                + ext_weights["weather_risk"] * weather_risk * 0.3
                + ext_weights["event_impact"] * event_impact * 0.2
            )

            forecast_raw = plan_value * (1 + internal_pct + external_pct)

            capacity_buffer = 0.9 + 0.1 * (1 - config.abwesenheiten / 0.12)
            capacity = base * capacity_buffer * (1 + 0.15 * seasonality - 0.5 * weekend_factor)

            noise_scale = base * 0.08
            actuals = max(0.0, forecast_raw + rng.normal(0, noise_scale))

            drivers = {
                "flu_index": plan_value * ext_weights["flu_index"] * flu_idx * 0.4,
                "weather_risk": plan_value * ext_weights["weather_risk"] * weather_risk * 0.3,
                "event_impact": plan_value * ext_weights["event_impact"] * event_impact * 0.2,
                "verweildauer": plan_value * verweildauer_pct,
                "op_zeiten": plan_value * op_zeiten_pct,
                "nurse_ratio": plan_value * nurse_ratio_pct,
                "abwesenheiten": plan_value * abwesenheiten_pct,
                "cluster": plan_value * cluster_pct,
            }

            driver_sum = sum(drivers.values())
            gap_total = forecast_raw - plan_value
            drivers["rest"] = gap_total - driver_sum

            data_rows.append(
                {
                    "date": current_date,
                    "resource": resource,
                    "plan": plan_value,
                    "forecast_raw": forecast_raw,
                    "capacity": capacity,
                    "actuals": actuals,
                    "weekday": weekday,
                    "week": current_date.isocalendar().week,
                    "flu_index": flu_idx,
                    "weather_risk": weather_risk,
                    "event_impact": event_impact,
                    "seasonality": seasonality,
                    "drivers": drivers,
                }
            )

    df = SimulationResult(data_rows)
    df = _apply_driver_columns(df)
    df = assimilate_forecasts(df, config, todays_date)

    df["gap"] = df["forecast"] - df["capacity"]
    df["norm_gap"] = df["gap"] / df["capacity"].where(df["capacity"] > 0, 1)
    df["actuals_to_date"] = np.where(
        df["date"].dt.date <= todays_date,
        df["actuals"],
        np.nan,
    )

    return df


def _apply_driver_columns(df: SimulationResult) -> SimulationResult:
    driver_keys = [
        "flu_index",
        "weather_risk",
        "event_impact",
        "verweildauer",
        "op_zeiten",
        "nurse_ratio",
        "abwesenheiten",
        "cluster",
        "rest",
    ]
    for key in driver_keys:
        df[f"driver_{key}"] = df["drivers"].apply(lambda d: float(d.get(key, 0.0)))
    return df


def assimilate_forecasts(
    df: SimulationResult,
    config: SimulationConfig,
    todays_date: date,
    alpha: float = 0.3,
) -> SimulationResult:
    """Assimilate actuals into forecasts based on rhythm (weekly/monthly)."""

    df = df.sort_values(["resource", "date"]).copy()
    adjusted = []
    rhythm = config.datenrhythmus.lower()

    def should_assimilate(timestamp: pd.Timestamp) -> bool:
        if timestamp.date() > todays_date:
            return False
        if rhythm.startswith("w"):
            return timestamp.weekday() == 6  # Sunday
        if rhythm.startswith("m"):
            return timestamp.day == 1
        return False

    for resource, group in df.groupby("resource", sort=False):
        correction = 0.0
        last_forecast = 0.0
        rows = []
        for _, row in group.iterrows():
            baseline_forecast = float(row["forecast_raw"])
            last_forecast = baseline_forecast + correction

            if should_assimilate(row["date"]):
                difference = float(row["actuals"]) - baseline_forecast
                correction = (1 - alpha) * correction + alpha * difference
                last_forecast = baseline_forecast + correction

            rows.append(last_forecast)
        adjusted.extend(rows)

    df["forecast"] = adjusted
    return df


def to_csv(df: SimulationResult) -> str:
    """Export helper for CSV download."""

    export_cols = [
        "date",
        "resource",
        "plan",
        "forecast",
        "capacity",
        "actuals",
        "actuals_to_date",
        "gap",
        "norm_gap",
        "driver_flu_index",
        "driver_weather_risk",
        "driver_event_impact",
        "driver_verweildauer",
        "driver_op_zeiten",
        "driver_nurse_ratio",
        "driver_abwesenheiten",
        "driver_cluster",
        "driver_rest",
    ]
    csv_buffer = df[export_cols].copy()
    csv_buffer["date"] = csv_buffer["date"].dt.strftime("%Y-%m-%d")
    return csv_buffer.to_csv(index=False, float_format="%.3f")


__all__ = [
    "SimulationConfig",
    "SimulationResult",
    "simulate_year",
    "assimilate_forecasts",
    "to_csv",
]
