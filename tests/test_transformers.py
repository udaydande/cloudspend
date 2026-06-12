import pandas as pd
import pytest
from datetime import date, timedelta

from cloudspend.extractors.seeder import generate
from cloudspend.transformers.aggregations import (
    daily_by_service,
    monthly_totals,
    top_services,
    detect_anomalies,
)


@pytest.fixture
def sample_df():
    return generate(months=2)


def test_seeder_generates_records(sample_df):
    assert len(sample_df) > 0
    assert "date" in sample_df.columns
    assert "cost" in sample_df.columns
    assert "service" in sample_df.columns


def test_daily_by_service(sample_df):
    result = daily_by_service(sample_df)
    assert "day" in result.columns
    assert "service" in result.columns
    assert "cost" in result.columns
    assert result["cost"].min() >= 0


def test_monthly_totals(sample_df):
    result = monthly_totals(sample_df)
    assert len(result) >= 2  # at least 2 months
    assert result["cost"].sum() == pytest.approx(sample_df["cost"].sum(), rel=1e-3)


def test_top_services_returns_n(sample_df):
    result = top_services(sample_df, n=3)
    assert len(result) <= 3
    # Should be sorted descending
    costs = result["total_cost"].tolist()
    assert costs == sorted(costs, reverse=True)


def test_detect_anomalies_returns_dataframe(sample_df):
    result = detect_anomalies(sample_df)
    assert isinstance(result, pd.DataFrame)
    # All flagged rows should have z_score > 2
    if not result.empty:
        assert (result["z_score"].abs() > 2.0).all()
