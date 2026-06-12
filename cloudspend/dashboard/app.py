"""
Plotly Dash dashboard for cloudspend analytics.
Run: python -m cloudspend.dashboard.app
"""

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from sqlalchemy import text

from cloudspend.loaders.sqlite_loader import get_engine
from cloudspend.transformers.aggregations import (
    monthly_totals,
    top_services,
    region_breakdown,
    detect_anomalies,
)

app = Dash(__name__, title="cloudspend")
engine = get_engine()


def load_df() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text("SELECT * FROM billing_records"), conn, parse_dates=["date"])


app.layout = html.Div(
    style={"fontFamily": "system-ui, sans-serif", "padding": "24px", "backgroundColor": "#f8fafc"},
    children=[
        html.H1("cloudspend", style={"fontSize": "1.5rem", "marginBottom": "4px"}),
        html.P("Infrastructure cost analytics", style={"color": "#64748b", "marginBottom": "24px"}),

        html.Div(id="summary-cards", style={"display": "flex", "gap": "16px", "marginBottom": "24px"}),

        html.Div([
            dcc.Graph(id="monthly-trend"),
        ], style={"marginBottom": "24px"}),

        html.Div([
            dcc.Graph(id="service-breakdown", style={"flex": 1}),
            dcc.Graph(id="region-breakdown", style={"flex": 1}),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "24px"}),

        html.H2("Anomalies", style={"fontSize": "1rem", "marginBottom": "8px"}),
        html.Div(id="anomaly-table"),

        dcc.Interval(id="refresh", interval=60_000, n_intervals=0),
    ],
)


@app.callback(
    Output("summary-cards", "children"),
    Output("monthly-trend", "figure"),
    Output("service-breakdown", "figure"),
    Output("region-breakdown", "figure"),
    Output("anomaly-table", "children"),
    Input("refresh", "n_intervals"),
)
def update(_n):
    df = load_df()

    # Summary cards
    total = df["cost"].sum()
    this_month = df[df["date"].dt.to_period("M") == pd.Timestamp.now().to_period("M")]["cost"].sum()
    anomalies = detect_anomalies(df)

    cards = [
        _card("Total Spend", f"${total:,.0f}"),
        _card("This Month", f"${this_month:,.0f}"),
        _card("Anomalies Detected", str(len(anomalies))),
    ]

    # Monthly trend
    monthly = monthly_totals(df)
    monthly["month_str"] = monthly["month"].astype(str)
    trend_fig = px.bar(monthly, x="month_str", y="cost", title="Monthly Spend",
                       labels={"month_str": "Month", "cost": "Cost (USD)"},
                       color_discrete_sequence=["#3b82f6"])
    trend_fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")

    # Service breakdown
    services = top_services(df)
    svc_fig = px.pie(services, names="service", values="total_cost",
                     title="Spend by Service", hole=0.4)
    svc_fig.update_layout(paper_bgcolor="white")

    # Region breakdown
    regions = region_breakdown(df)
    reg_fig = px.bar(regions, x="total_cost", y="region", orientation="h",
                     title="Spend by Region", labels={"total_cost": "Cost (USD)"},
                     color_discrete_sequence=["#8b5cf6"])
    reg_fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", yaxis={"autorange": "reversed"})

    # Anomaly table
    if anomalies.empty:
        anomaly_html = html.P("No anomalies detected.", style={"color": "#64748b"})
    else:
        anomaly_html = html.Table(
            [html.Tr([html.Th(c) for c in ["Date", "Service", "Cost", "Expected", "Z-Score"]])] +
            [
                html.Tr([
                    html.Td(str(r["day"])[:10]),
                    html.Td(r["service"]),
                    html.Td(f"${r['cost']:,.2f}"),
                    html.Td(f"${r['rolling_mean']:,.2f}"),
                    html.Td(f"{r['z_score']:.1f}"),
                ]) for _, r in anomalies.iterrows()
            ],
            style={"borderCollapse": "collapse", "width": "100%", "fontSize": "0.875rem"},
        )

    return cards, trend_fig, svc_fig, reg_fig, anomaly_html


def _card(label: str, value: str):
    return html.Div([
        html.P(label, style={"fontSize": "0.75rem", "color": "#64748b", "margin": 0}),
        html.P(value, style={"fontSize": "1.5rem", "fontWeight": "600", "margin": 0}),
    ], style={"background": "white", "padding": "16px", "borderRadius": "8px",
               "boxShadow": "0 1px 3px rgba(0,0,0,0.08)", "minWidth": "160px"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
