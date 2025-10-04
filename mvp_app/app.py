"""Streamlit MVP für Kapazitätsplanung."""
from __future__ import annotations
from datetime import date
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from mvp_app.kpis import compute_kpis, top_drivers_for_date, weekly_sparkline
    from mvp_app.logic import AMPel_COLORS, AmpelThresholds, describe_cell
    from mvp_app.simulate import SimulationConfig, simulate_year, to_csv
    from mvp_app.utils import figure_to_svg_bytes, format_number, format_percentage
except ModuleNotFoundError:  # Allow running via ``streamlit run mvp_app/app.py``
    import sys
    from pathlib import Path

    _PKG_DIR = Path(__file__).resolve().parent
    if str(_PKG_DIR) not in sys.path:
        sys.path.insert(0, str(_PKG_DIR))

    from kpis import compute_kpis, top_drivers_for_date, weekly_sparkline
    from logic import AMPel_COLORS, AmpelThresholds, describe_cell
    from simulate import SimulationConfig, simulate_year, to_csv
    from utils import figure_to_svg_bytes, format_number, format_percentage


DEFAULT_YEAR = date.today().year
DEFAULT_PARAMS = {
    "param_year": DEFAULT_YEAR,
    "param_seed": 42,
    "param_budget": 0.03,
    "param_verweildauer": 0.2,
    "param_op_zeiten": 5.0,
    "param_nurse_ratio": 5.0,
    "param_abwesenheiten": 0.06,
    "param_cluster": 4,
    "param_saison": 1.0,
    "param_flu": 0.8,
    "param_weather": 0.6,
    "param_rhythm": "wöchentlich",
    "param_ampel_gruen": 0.05,
    "param_ampel_gelb": 0.15,
}

import plotly.io as pio

# Configure Kaleido for headless Chromium on Streamlit Cloud
# (do this before any fig.to_image() calls)
def _configure_kaleido():
    # Optional defaults
    pio.kaleido.scope.default_format = "png"
    pio.kaleido.scope.default_width = 1200
    pio.kaleido.scope.default_height = 700
    # Headless Chromium args
    pio.kaleido.scope.chromium_args = [
        "--headless",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--single-process",
        "--disable-gpu",
    ]

try:
    _configure_kaleido()
except Exception as e:
    # Don't crash the app if Kaleido isn't used;
    # you can log or print for debugging
    print(f"Kaleido setup warning: {e}")


def reset_defaults() -> None:
    for key, value in DEFAULT_PARAMS.items():
        st.session_state[key] = value


def sidebar_controls() -> Dict[str, float | int | str]:
    st.sidebar.header("Einstellungen")
    if "param_year" not in st.session_state:
        reset_defaults()

    if st.sidebar.button("Standardwerte", type="secondary"):
        reset_defaults()
        st.rerun()

    st.sidebar.caption("Interne Faktoren")
    year = st.sidebar.number_input(
        "Jahr", min_value=2020, max_value=2035, step=1, key="param_year"
    )
    seed = st.sidebar.number_input(
        "Seed", min_value=1, max_value=9999, step=1, key="param_seed"
    )
    budget = st.sidebar.slider(
        "Budgetiertes Wachstum",
        min_value=0.0,
        max_value=0.20,
        step=0.01,
        format="%0.02f",
        key="param_budget",
    )
    verweildauer = st.sidebar.slider(
        "Verweildauer-Delta (Tage)",
        min_value=-1.0,
        max_value=2.0,
        step=0.1,
        key="param_verweildauer",
    )
    op_delta = st.sidebar.slider(
        "OP-Zeiten-Delta (Minuten)",
        min_value=-20.0,
        max_value=25.0,
        step=1.0,
        key="param_op_zeiten",
    )
    nurse_ratio = st.sidebar.slider(
        "Patient-Pflege-Ratio",
        min_value=3.0,
        max_value=8.0,
        step=0.1,
        key="param_nurse_ratio",
    )
    abwesenheiten = st.sidebar.slider(
        "Abwesenheiten / Urlaub (%)",
        min_value=0.0,
        max_value=0.20,
        step=0.01,
        key="param_abwesenheiten",
    )
    cluster = st.sidebar.slider(
        "Stationen-Cluster",
        min_value=2,
        max_value=10,
        step=1,
        key="param_cluster",
    )

    st.sidebar.caption("Externe Faktoren")
    saison = st.sidebar.slider(
        "Saisonalität (Stärke)",
        min_value=0.0,
        max_value=2.0,
        step=0.1,
        key="param_saison",
    )
    flu = st.sidebar.slider(
        "Epidemie/Grippe-Index",
        min_value=0.0,
        max_value=1.5,
        step=0.1,
        key="param_flu",
    )
    weather = st.sidebar.slider(
        "Wetter-/Unfalltreiber",
        min_value=0.0,
        max_value=1.5,
        step=0.1,
        key="param_weather",
    )

    st.sidebar.caption("Datenrhythmus")
    rhythm = st.sidebar.radio(
        "Assimilation",
        ["wöchentlich", "monatlich"],
        key="param_rhythm",
        horizontal=True,
    )

    st.sidebar.caption("Ampel-Schwellen")
    green = st.sidebar.slider(
        "Grün-Puffer",
        min_value=0.01,
        max_value=0.10,
        step=0.01,
        key="param_ampel_gruen",
    )
    yellow = st.sidebar.slider(
        "Gelb ab Norm-Gap",
        min_value=0.05,
        max_value=0.30,
        step=0.01,
        key="param_ampel_gelb",
    )

    return {
        "year": int(year),
        "seed": int(seed),
        "budget": float(budget),
        "verweildauer": float(verweildauer),
        "op_delta": float(op_delta),
        "nurse_ratio": float(nurse_ratio),
        "abwesenheiten": float(abwesenheiten),
        "cluster": int(cluster),
        "saison": float(saison),
        "flu": float(flu),
        "weather": float(weather),
        "rhythm": str(rhythm),
        "green": float(green),
        "yellow": float(yellow),
    }


@st.cache_data(show_spinner=False)
def load_simulation(params: Dict[str, float | int | str]) -> pd.DataFrame:
    config = SimulationConfig(
        year=params["year"],
        seed=params["seed"],
        budget_growth=params["budget"],
        verweildauer_delta=params["verweildauer"],
        op_zeiten_delta=params["op_delta"],
        nurse_ratio=params["nurse_ratio"],
        abwesenheiten=params["abwesenheiten"],
        cluster_anzahl=params["cluster"],
        saisonalitaet_staerke=params["saison"],
        flu_index_staerke=params["flu"],
        weather_risk_staerke=params["weather"],
        datenrhythmus=params["rhythm"],
    )
    df = simulate_year(config)
    return df


def build_line_chart(df: pd.DataFrame, resource: str) -> go.Figure:
    filtered = df[df["resource"] == resource]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=filtered["date"],
            y=filtered["plan"],
            mode="lines",
            name="Plan (Soll)",
            line=dict(color="#424242", width=2, dash="solid"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=filtered["date"],
            y=filtered["forecast"],
            mode="lines",
            name="Prognose",
            line=dict(color="#1b5e20", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=filtered["date"],
            y=filtered["capacity"],
            mode="lines",
            name="Verfügbare Kapazität",
            line=dict(color="#0d47a1", width=2, dash="dot"),
        )
    )

    fig.update_layout(
        margin=dict(l=30, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Datum",
        yaxis_title="Einheiten",
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


def build_heatmap(
    df: pd.DataFrame, thresholds: AmpelThresholds, nurse_ratio: float
) -> Tuple[go.Figure, List[Dict[str, float | str]]]:
    grouped = (
        df.groupby(["week", "resource"], as_index=False)
        .agg(gap_sum=("gap", "sum"), capacity_sum=("capacity", "sum"), days=("gap", "size"))
    )
    grouped["norm_gap"] = grouped.apply(
        lambda row: (row["gap_sum"] / row["capacity_sum"])
        if row["capacity_sum"]
        else 0.0,
        axis=1,
    )
    grouped.rename(columns={"gap_sum": "gap"}, inplace=True)

    pivot = grouped.pivot(index="resource", columns="week", values="norm_gap")
    weeks = sorted(df["week"].unique())
    resources = sorted(df["resource"].unique())

    cell_details: Dict[Tuple[str, int], Dict[str, float | str]] = {}
    for _, row in grouped.iterrows():
        cell_details[(row["resource"], int(row["week"]))] = describe_cell(row, thresholds, nurse_ratio)

    hover_text: List[List[str]] = []
    for resource in resources:
        row_text = []
        for week in weeks:
            detail = cell_details.get(
                (resource, int(week)),
                {
                    "status": "Keine Daten",
                    "farbe": "#9e9e9e",
                    "gap": float("nan"),
                    "norm_gap": float("nan"),
                    "empfehlung": "Keine Daten verfügbar",
                },
            )
            row_text.append(
                "<br>".join(
                    [
                        f"KW {week}",
                        f"Ressource: {resource}",
                        f"Status: {detail['status']}",
                        f"Norm-Gap: {detail['norm_gap']:.1%}" if pd.notna(detail["norm_gap"]) else "Norm-Gap: –",
                        f"Gap: {detail['gap']:.1f}" if pd.notna(detail["gap"]) else "Gap: –",
                        f"Empfehlung: {detail['empfehlung']}",
                    ]
                )
            )
        hover_text.append(row_text)

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=pivot.reindex(index=resources, columns=weeks).values,
                x=weeks,
                y=resources,
                colorscale="RdYlGn_r",
                zmin=-0.3,
                zmax=0.3,
                colorbar=dict(title="Norm-Gap"),
                hoverinfo="text",
                text=hover_text,
            )
        ]
    )
    fig.update_layout(
        xaxis_title="Kalenderwoche",
        yaxis_title="Ressource",
        margin=dict(l=40, r=40, t=30, b=40),
        template="plotly_white",
    )

    # Prepare a list for detail view below the heatmap
    status_rank = {"ROT": 0, "GELB": 1, "GRÜN": 2, "BLAU": 3}
    detail_rows = [detail for detail in cell_details.values()]
    detail_rows.sort(
        key=lambda item: (
            status_rank.get(str(item["status"]), 4),
            -abs(float(item.get("norm_gap", 0.0))),
        )
    )
    return fig, detail_rows


def render_kpi_cards(kpis: Dict[str, float]) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Auslastung", format_percentage(kpis["Auslastung"]))
    col2.metric("Prognosefehler (MAPE)", format_percentage(kpis["MAPE"]))
    col3.metric("Wartetage", format_number(kpis["Wartetage"]))
    col4.metric("Stornoquote", format_percentage(kpis["Stornoquote"]))
    col5.metric("Pflege-Engpass", format_number(kpis["Pflege-Engpass"]))


def render_top_drivers(drivers) -> None:
    st.subheader("Top-Treiber")
    if not drivers:
        st.write("Keine Treiber verfügbar.")
        return
    for label, value in drivers:
        st.write(f"• {label}: {format_number(value, digits=1)}")


def render_weekly_sparkline(data: pd.DataFrame) -> None:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["week"],
            y=data["actuals"],
            name="Ist",
            mode="lines+markers",
            line=dict(color="#1b5e20"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["week"],
            y=data["forecast"],
            name="Prognose",
            mode="lines",
            line=dict(color="#f9a825", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["week"],
            y=data["capacity"],
            name="Kapazität",
            mode="lines",
            line=dict(color="#0d47a1", dash="dot"),
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=20, b=30),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="KW",
        yaxis_title="Aggregiert",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def main():
    st.set_page_config(
        page_title="Kapazitätsplanung Co-Pilot",
        page_icon="📊",
        layout="wide",
    )
    params = sidebar_controls()
    df = load_simulation(params)
    thresholds = AmpelThresholds(params["green"], params["yellow"])
    today = date.today()

    st.title("Kapazitätsplanung – Low-Fi MVP")
    st.caption("Plan vs. Prognose, Ampelsystem und Handlungsempfehlungen mit synthetischen Daten")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        if st.button("Prognose aktualisieren", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col_right:
        csv_string = to_csv(df)
        st.download_button(
            "Export CSV",
            data=csv_string,
            file_name="kapazitaet_dashboard.csv",
            mime="text/csv",
        )

    tab_plan, tab_control = st.tabs(["Jahresplanung", "Prognose & Steuerung"])

    with tab_plan:
        st.subheader("Jahresverlauf")
        resource = st.selectbox("Ressource", df["resource"].unique())
        fig_line = build_line_chart(df, resource)
        st.plotly_chart(fig_line, use_container_width=True, config={"displaylogo": False})
        svg_bytes = figure_to_svg_bytes(fig_line)
        st.download_button(
            "Download SVG",
            data=svg_bytes,
            file_name=f"jahresverlauf_{resource}.svg",
            mime="image/svg+xml",
        )

        kpis = compute_kpis(df, today, thresholds)
        render_kpi_cards(kpis)

    with tab_control:
        st.subheader("Ampel-Heatmap & Empfehlungen")
        fig_heatmap, details = build_heatmap(df, thresholds, params["nurse_ratio"])
        st.plotly_chart(fig_heatmap, use_container_width=True, config={"displaylogo": False})

        st.markdown("**Empfehlungen (Top Kritikalität)**")
        for detail in details[:5]:
            st.write(
                f"KW {detail['kw']} – {detail['resource']}: {detail['status']} • Gap {detail['gap']:.1f} → {detail['empfehlung']}"
            )

        spark = weekly_sparkline(df, today)
        st.markdown("**Wochen-Sparkline**")
        render_weekly_sparkline(spark)

        drivers = top_drivers_for_date(df, today)
        render_top_drivers(drivers)


if __name__ == "__main__":
    main()
