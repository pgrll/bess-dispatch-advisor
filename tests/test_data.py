"""Data must be rejected loudly when incomplete, and parsed exactly when not."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bess_advisor.data.entsoe import EntsoeError, build_request_params, explain_http_error, parse_day_ahead_xml
from bess_advisor.data.storage import load_prices_csv, save_prices_csv
from bess_advisor.data.validation import PriceDataError, expected_intervals, validate_day_prices
from tests.conftest import make_day

FIXTURES = Path(__file__).parent / "fixtures"


# --- Validation -------------------------------------------------------------


@pytest.mark.parametrize(("day", "n"), [(date(2026, 11, 14), 96), (date(2026, 3, 29), 92), (date(2026, 10, 25), 100)])
def test_expected_intervals_handle_clock_changes(day, n):
    assert expected_intervals(day) == n


def test_complete_day_passes():
    prices = validate_day_prices(make_day(np.arange(96.0)))
    assert len(prices) == 96 and prices.name == "price_eur_mwh"


def test_empty_series_is_rejected():
    with pytest.raises(PriceDataError, match="empty"):
        validate_day_prices(pd.Series(dtype=float))


def test_missing_price_is_rejected():
    prices = make_day(np.arange(96.0))
    prices.iloc[40] = np.nan
    with pytest.raises(PriceDataError, match="no price"):
        validate_day_prices(prices)


def test_gap_in_the_day_is_rejected():
    with pytest.raises(PriceDataError, match="15-minute"):
        validate_day_prices(make_day(np.arange(96.0)).drop(index=make_day(np.arange(96.0)).index[50]))


def test_hourly_prices_are_rejected():
    hourly = pd.Series(np.arange(24.0), index=pd.date_range("2026-11-14", periods=24, freq="h", tz="Europe/Paris"))
    with pytest.raises(PriceDataError):
        validate_day_prices(hourly)


def test_partial_day_is_rejected():
    with pytest.raises(PriceDataError, match="Expected 96"):
        validate_day_prices(make_day(np.arange(80.0)))


def test_naive_timestamps_are_rejected():
    naive = pd.Series(np.arange(96.0), index=pd.date_range("2026-11-14", periods=96, freq="15min"))
    with pytest.raises(PriceDataError, match="timezone"):
        validate_day_prices(naive)


# --- ENTSO-E parsing ----------------------------------------------------------


def fixture_prices() -> list[float]:
    """The prices written into the fixture (see the generation in the file header)."""
    prices = [round(50 + (i % 12) * 2.5, 2) for i in range(96)]
    for i in range(10, 14):
        prices[i] = prices[9]
    return prices


def test_parser_keeps_15_minute_series_and_forward_fills_a03():
    xml = (FIXTURES / "entsoe_a44_2026-04-18.xml").read_text()
    prices = validate_day_prices(parse_day_ahead_xml(xml), date(2026, 4, 18))
    assert len(prices) == 96
    assert prices.tolist() == fixture_prices()
    assert prices.index[0] == pd.Timestamp("2026-04-18 00:00", tz="Europe/Paris")


def test_parser_can_read_the_hourly_series():
    xml = (FIXTURES / "entsoe_a44_2026-04-18.xml").read_text()
    hourly = parse_day_ahead_xml(xml, resolution="PT60M")
    assert len(hourly) == 24 and hourly.iloc[0] == 40.0


def test_acknowledgement_document_raises_with_its_reason():
    xml = (FIXTURES / "entsoe_ack_no_data.xml").read_text()
    with pytest.raises(EntsoeError, match="No matching data"):
        parse_day_ahead_xml(xml)


def test_request_covers_the_local_day_in_utc():
    params = build_request_params(date(2026, 3, 29), token="t")
    assert params["periodStart"] == "202603282300"  # 00:00 CET
    assert params["periodEnd"] == "202603292200"  # 00:00 CEST the next day
    assert params["documentType"] == "A44"


# --- Storage ----------------------------------------------------------------


def test_csv_round_trip_on_a_clock_change_day(tmp_path):
    prices = validate_day_prices(make_day(np.arange(100.0), day="2026-10-25"))
    path = save_prices_csv(prices, tmp_path / "day.csv")
    reloaded = validate_day_prices(load_prices_csv(path))
    assert reloaded.tolist() == prices.tolist()
    assert (reloaded.index == prices.index).all()


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, "token"), (429, "Wait a minute"), (503, "unavailable"), (400, "refused")],
)
def test_http_errors_say_what_to_do(status, expected):
    assert expected in explain_http_error(status, "")


def test_http_error_with_acknowledgement_keeps_the_platform_reason():
    body = (FIXTURES / "entsoe_ack_no_data.xml").read_text()
    assert "No matching data" in explain_http_error(400, body)
