"""The report shows where data comes from, the exact intervals, and no orders."""

from __future__ import annotations

from pathlib import Path

from bess_advisor.cli import main

SAMPLE = Path(__file__).parents[1] / "data" / "sample" / "synthetic_day.csv"


def test_report_on_the_sample_day(capsys):
    main(["--prices", str(SAMPLE)])
    report = capsys.readouterr().out
    assert "SYNTHETIC" in report
    assert "96 intervals of 15 min" in report
    assert "Scenarios, ranked by net value captured (EUR)" in report
    assert "decision stays with the analyst" in report
    # Intervals are listed one by one at 15-minute granularity, never merged.
    assert "13:30-13:45  charge" in report
