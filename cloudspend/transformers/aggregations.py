"""
Transformers: aggregations and anomaly detection on normalized billing data.
"""

import numpy as np
import pandas as pd


def daily_by_service(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily cost per service."""
    return (
        df.groupby([df["date"].dt.date, "service"])["cost"]
        .sum()
        .reset_index()
        .rename(columns={"date": "day"})
        .sort_values("day")
    )


def monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly total spend."""
    return (
        df.assign(month=df["date"].dt.to_period("M"))
        .groupby("month")["cost"]
        .sum()
        .reset_index()
        .sort_values("month")
    )


def top_services(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N services by total cost."""
    return (
        df.groupby("service")["cost"]
        .sum()
        .nlargest(n)
        .reset_index()
        .rename(columns={"cost": "total_cost"})
    )


def region_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("region")["cost"]
        .sum()
        .reset_index()
        .rename(columns={"cost": "total_cost"})
        .sort_values("total_cost", ascending=False)
    )


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> pd.DataFrame:
    """
    Flag daily cost entries that deviate more than z_threshold standard
    deviations from the service's rolling 7-day mean.
    """
    daily = daily_by_service(df)
    daily["day"] = pd.to_datetime(daily["day"])

    results = []
    for service, group in daily.groupby("service"):
        group = group.sort_values("day").copy()
        group["rolling_mean"] = group["cost"].rolling(7, min_periods=1).mean()
        group["rolling_std"] = group["cost"].rolling(7, min_periods=1).std().fillna(0)
        group["z_score"] = np.where(
            group["rolling_std"] > 0,
            (group["cost"] - group["rolling_mean"]) / group["rolling_std"],
            0,
        )
        group["is_anomaly"] = group["z_score"].abs() > z_threshold
        group["service"] = service
        results.append(group)

    return pd.concat(results).query("is_anomaly")[
        ["day", "service", "cost", "rolling_mean", "z_score"]
    ].sort_values("day")
