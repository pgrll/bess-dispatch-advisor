"""Day-ahead prices from the ENTSO-E Transparency Platform.

The platform returns XML documents of type A44 (price document). This
module keeps the network call and the parsing separate, so the parser can
be tested offline on a saved document.

Two details of the format matter for correctness:

* Since the 15-minute day-ahead go-live, a document may hold several time
  series at different resolutions. We select the one we ask for and fail
  loudly if it is missing, rather than silently mixing resolutions.
* With curve type ``A03`` ENTSO-E omits a point when its price equals the
  previous point's. Missing positions must be forward-filled, otherwise a
  day with flat periods looks like a day with missing data.

API documentation: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

import pandas as pd

from bess_advisor.data.validation import MARKET_TIMEZONE, validate_day_prices

API_URL = "https://web-api.tp.entsoe.eu/api"
FRANCE_BIDDING_ZONE = "10YFR-RTE------C"
TOKEN_ENV_VAR = "ENTSOE_API_TOKEN"

_RESOLUTIONS = {"PT15M": pd.Timedelta(minutes=15), "PT60M": pd.Timedelta(hours=1)}


class EntsoeError(RuntimeError):
    """Raised when ENTSO-E returns no usable price data."""


def _local_name(tag: str) -> str:
    """Strip the XML namespace, which changes between document versions."""
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _child_text(element: ET.Element, name: str) -> str:
    matches = _children(element, name)
    if not matches or matches[0].text is None:
        raise EntsoeError(f"Malformed document: <{name}> missing under <{_local_name(element.tag)}>.")
    return matches[0].text.strip()


def parse_day_ahead_xml(xml_text: str, resolution: str = "PT15M") -> pd.Series:
    """Parse an A44 price document into a price series.

    Args:
        xml_text: Raw XML returned by the API.
        resolution: ISO 8601 resolution to keep (``"PT15M"`` or ``"PT60M"``).

    Returns:
        Prices in EUR/MWh indexed by the UTC start of each interval.

    Raises:
        EntsoeError: If the document is an error acknowledgement or holds
            no period at the requested resolution.
    """
    if resolution not in _RESOLUTIONS:
        raise ValueError(f"Unsupported resolution {resolution!r}")
    step = _RESOLUTIONS[resolution]
    root = ET.fromstring(xml_text)

    if _local_name(root.tag) == "Acknowledgement_MarketDocument":
        reasons = [_child_text(r, "text") for r in root.iter() if _local_name(r.tag) == "Reason"]
        raise EntsoeError("ENTSO-E returned no data: " + "; ".join(reasons or ["no reason given"]))

    prices: dict[pd.Timestamp, float] = {}
    for series in (e for e in root.iter() if _local_name(e.tag) == "TimeSeries"):
        curve_type = _children(series, "curveType")
        forward_fill = bool(curve_type) and (curve_type[0].text or "").strip() == "A03"
        for period in _children(series, "Period"):
            if _child_text(period, "resolution") != resolution:
                continue
            interval = _children(period, "timeInterval")[0]
            start = pd.Timestamp(_child_text(interval, "start")).tz_convert("UTC")
            end = pd.Timestamp(_child_text(interval, "end")).tz_convert("UTC")
            n_slots = int((end - start) / step)

            points = {
                int(_child_text(p, "position")): float(_child_text(p, "price.amount"))
                for p in _children(period, "Point")
            }
            last_price: float | None = None
            for position in range(1, n_slots + 1):
                if position in points:
                    last_price = points[position]
                elif not forward_fill or last_price is None:
                    continue  # a genuine gap, caught by validation downstream
                prices[start + (position - 1) * step] = last_price

    if not prices:
        raise EntsoeError(f"The document holds no {resolution} prices.")
    series = pd.Series(prices, name="price_eur_mwh").sort_index()
    series.index.name = "interval_start_utc"
    return series


def build_request_params(delivery_day: date, token: str, bidding_zone: str = FRANCE_BIDDING_ZONE) -> dict[str, str]:
    """Query parameters for one delivery day, expressed in market local time."""
    start = pd.Timestamp(delivery_day, tz=MARKET_TIMEZONE).tz_convert("UTC")
    end = pd.Timestamp(delivery_day + pd.Timedelta(days=1), tz=MARKET_TIMEZONE).tz_convert("UTC")
    return {
        "securityToken": token,
        "documentType": "A44",
        "in_Domain": bidding_zone,
        "out_Domain": bidding_zone,
        "periodStart": start.strftime("%Y%m%d%H%M"),
        "periodEnd": end.strftime("%Y%m%d%H%M"),
    }


def fetch_day_ahead_prices(delivery_day: date, token: str | None = None, timeout_s: float = 30.0) -> pd.Series:
    """Download and validate the French day-ahead prices of one day.

    The token is read from the ``ENTSOE_API_TOKEN`` environment variable
    when not given. Request one for free from the Transparency Platform
    (account settings, "Web API Security Token").
    """
    token = token or os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise EntsoeError(f"No API token: set the {TOKEN_ENV_VAR} environment variable.")
    url = f"{API_URL}?{urllib.parse.urlencode(build_request_params(delivery_day, token))}"
    with urllib.request.urlopen(url, timeout=timeout_s) as response:  # noqa: S310 (fixed https URL)
        xml_text = response.read().decode("utf-8")
    return validate_day_prices(parse_day_ahead_xml(xml_text), delivery_day)
