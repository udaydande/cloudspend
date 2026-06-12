"""
Plotly Dash dashboard for cloudspend analytics.
Run: python -m cloudspend.dashboard.app
"""

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, ctx
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

ACCENT = "#3b82f6"
PURPLE = "#8b5cf6"
CARD_STYLE = {
    "background": "white",
    "padding": "16px",
    "borderRadius": "10px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.08)",
    "minWidth": "160px",
}
PAGE_STYLE = {
    "fontFamily": "system-ui, sans-serif",
    "padding": "28px",
    "backgroundColor": "#f1f5f9",
    "minHeight": "100vh",
}


def load_df() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT * FROM billing_records"), conn, parse_dates=["date"]
        )


app.layout = html.Div(style=PAGE_STYLE, children=[

    html.Div(style={"display": "flex", "justifyContent": "space-between",
                    "alignItems": "center", "marginBottom": "24px"}, children=[
        html.Div([
            html.H1("cloudspend", style={"fontSize": "1.75rem", "fontWeight": "700",
                                         "margin": 0, "color": "#0f172a"}),
            html.P("Infrastructure cost analytics",
                   style={"color": "#64748b", "margin": "4px 0 0 0", "fontSize": "0.9rem"}),
        ]),
        html.Button("Reset Filters", id="reset-btn",
                    style={"padding": "8px 18px", "borderRadius": "8px",
                           "border": "1px solid #cbd5e1", "backgroundColor": "white",
                           "cursor": "pointer", "fontSize": "0.85rem",
                           "color": "#475569", "fontWeight": "500"}),
    ]),

    html.Div(id="filter-banner", style={"marginBottom": "16px"}),

    html.Div(id="summary-cards",
             style={"display": "flex", "gap": "16px", "marginBottom": "24px",
                    "flexWrap": "wrap"}),

    html.Div([
        dcc.Graph(id="monthly-trend", config={"displayModeBar": False}),
    ], style={"backgroundColor": "white", "borderRadius": "12px",
               "padding": "8px", "marginBottom": "20px",
               "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}),

    html.Div(style={"display": "flex", "gap": "20px", "marginBottom": "20px"}, children=[
        html.Div([
            dcc.Graph(id="service-breakdown", config={"displayModeBar": False}),
        ], style={"flex": 1, "backgroundColor": "white", "borderRadius": "12px",
                   "padding": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}),
        html.Div([
            dcc.Graph(id="region-breakdown", config={"displayModeBar": False}),
        ], style={"flex": 1, "backgroundColor": "white", "borderRadius": "12px",
                   "padding": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}),
    ]),

    html.Div([
        html.H2("Anomalies", style={"fontSize": "1rem", "fontWeight": "600",
                                     "margin": "0 0 12px 0", "color": "#0f172a"}),
        html.Div(id="anomaly-table"),
    ], style={"backgroundColor": "white", "borderRadius": "12px", "padding": "20px",
               "boxShadow": "0 1px 3px rgba(0,0,0,0.06)"}),

    dcc.Store(id="selected-service", data=None),
    dcc.Store(id="selected-region", data=None),
    dcc.Interval(id="refresh", interval=60_000, n_intervals=0),
])


@app.callback(
    Output("selected-service", "data"),
    Output("selected-region", "data"),
    Input("service-breakdown", "clickData"),
    Input("region-breakdown", "clickData"),
    Input("reset-btn", "n_clicks"),
    State("selected-service", "data"),
    State("selected-region", "data"),
)
def update_filters(svc_click, reg_click, reset_clicks, cur_svc, cur_reg):
    triggered = ctx.triggered_id
    if triggered == "reset-btn":
        return None, None
    if triggered == "service-breakdown" and svc_click:
        clicked = svc_click["points"][0]["label"]
        return (None if clicked == cur_svc else clicked), cur_reg
    if triggered == "region-breakdown" and reg_click:
        clicked = reg_click["points"][0]["y"]
        return cur_svc, (None if clicked == cur_reg else clicked)
    return cur_svc, cur_reg


@app.callback(
    Output("filter-banner", "children"),
    Output("summary-cards", "children"),
    Output("monthly-trend", "figure"),
    Output("service-breakdown", "figure"),
    Output("region-breakdown", "figure"),
    Output("anomaly-table", "children"),
    Input("selected-service", "data"),
    Input("selected-region", "data"),
    Input("refresh", "n_intervals"),
)
def update_charts(selected_service, selected_region, _n):
    df = load_df()
    filtered = df.copy()
    if selected_service:
        filtered = filtered[filtered["service"] == selected_service]
    if selected_region:
        filtered = filtered[filtered["region"] == selected_region]

    active = []
    if selected_service:
        active.append(f"Service: {selected_service}")
    if selected_region:
        active.append(f"Region: {selected_region}")

    banner = html.Div(
        f"Filtered by → {' · '.join(active)}  (click again or Reset to clear)",
        style={"backgroundColor": "#eff6ff", "border": "1px solid #bfdbfe",
               "color": "#1d4ed8", "borderRadius": "8px",
               "padding": "8px 14px", "fontSize": "0.85rem"},
    ) if active else html.Div()

    total = filtered["cost"].sum()
    this_month = filtered[
        filtered["date"].dt.to_period("M") == pd.Timestamp.now().to_period("M")
    ]["cost"].sum()
    anomalies = detect_anomalies(filtered)

    cards = [
        _card("Total Spend", f"${total:,.0f}"),
        _card("This Month", f"${this_month:,.0f}"),
        _card("Anomalies", str(len(anomalies))),
        _card("Services", str(filtered["service"].nunique())),
        _card("Regions", str(filtered["region"].nunique())),
    ]

    monthly = monthly_totals(filtered)
    monthly["month_str"] = monthly["month"].astype(str)
    trend_fig = px.bar(
        monthly, x="month_str", y="cost",
        title=f"Monthly Spend{' — ' + selected_service if selected_service else ''}",
        labels={"month_str": "Month", "cost": "Cost (USD)"},
        color_discrete_sequence=[ACCENT],
    )
    trend_fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                             margin={"t": 40, "b": 20, "l": 20, "r": 20},
                             title_font_size=14)

    services = top_services(df)
    pull = [0.08 if selected_service and row["service"] == selected_service else 0
            for _, row in services.iterrows()]
    svc_fig = px.pie(services, names="service", values="total_cost",
                     title="Spend by Service", hole=0.4)
    svc_fig.update_traces(pull=pull, textposition="inside")
    svc_fig.update_layout(paper_bgcolor="white",
                           margin={"t": 40, "b": 20, "l": 20, "r": 20},
                           title_font_size=14)

    regions = region_breakdown(df)
    colors = [
        "#f59e0b" if selected_region and row["region"] == selected_region else PURPLE
        for _, row in regions.iterrows()
    ]
    reg_fig = px.bar(regions, x="total_cost", y="region", orientation="h",
                     title="Spend by Region", labels={"total_cost": "Cost (USD)"})
    reg_fig.update_traces(marker_color=colors)
    reg_fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           yaxis={"autorange": "reversed"},
                           margin={"t": 40, "b": 20, "l": 20, "r": 20},
                           title_font_size=14)

    th_style = {"padding": "8px 12px", "textAlign": "left",
                "backgroundColor": "#f8fafc", "fontWeight": "600",
                "fontSize": "0.8rem", "color": "#475569",
                "borderBottom": "2px solid #e2e8f0"}
    td_style = {"padding": "8px 12px", "fontSize": "0.85rem",
                "borderBottom": "1px solid #f1f5f9"}

    anomaly_content = html.P("No anomalies detected.",
                              style={"color": "#64748b", "fontSize": "0.875rem"}) \
        if anomalies.empty else html.Table(
        [html.Tr([html.Th(c, style=th_style)
                  for c in ["Date", "Service", "Cost", "Expected", "Z-Score"]])] +
        [
            html.Tr([
                html.Td(str(r["day"])[:10], style=td_style),
                html.Td(r["service"], style=td_style),
                html.Td(f"${r['cost']:,.2f}",
                        style={**td_style, "color": "#ef4444", "fontWeight": "600"}),
                html.Td(f"${r['rolling_mean']:,.2f}", style=td_style),
                html.Td(f"{r['z_score']:.1f}x", style=td_style),
            ]) for _, r in anomalies.iterrows()
        ],
        style={"borderCollapse": "collapse", "width": "100%"},
    )

    return banner, cards, trend_fig, svc_fig, reg_fig, anomaly_content


def _card(label: str, value: str):
    return html.Div([
        html.P(label, style={"fontSize": "0.72rem", "color": "#64748b",
                              "margin": "0 0 4px 0", "textTransform": "uppercase",
                              "letterSpacing": "0.05em"}),
        html.P(value, style={"fontSize": "1.4rem", "fontWeight": "700",
                              "margin": 0, "color": "#0f172a"}),
    ], style=CARD_STYLE)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
