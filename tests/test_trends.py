"""Tests for the phase 1 trend statistics, using synthetic signals only."""

import numpy as np
import pandas as pd
import pytest

from bearing_monitor import io, trends


def test_statistics_of_a_sine():
    t = np.arange(20_000) / 20_000.0
    signal = 2.0 * np.sin(2 * np.pi * 50.0 * t)

    result = trends.snapshot_statistics(signal)

    assert result["rms"] == pytest.approx(2.0 / np.sqrt(2.0), rel=1e-6)
    assert result["kurtosis"] == pytest.approx(1.5, rel=1e-3)
    assert result["peak"] == pytest.approx(2.0, rel=1e-6)


def test_kurtosis_of_gaussian_noise_is_three_and_rises_with_impulses():
    noise = np.random.default_rng(0).normal(size=200_000)
    impulsive = noise.copy()
    impulsive[::1000] += 15.0  # periodic impacts, as from a local bearing defect

    assert trends.snapshot_statistics(noise)["kurtosis"] == pytest.approx(3.0, abs=0.05)
    assert trends.snapshot_statistics(impulsive)["kurtosis"] > 10.0


def test_compute_trends_layout_and_flatline(tmp_path):
    rng = np.random.default_rng(1)
    names = ["2004.02.12.10.32.39", "2004.02.12.10.42.39", "2004.02.12.10.52.39"]
    for i, name in enumerate(names):
        data = rng.normal(scale=0.1, size=(256, 4)) if i < 2 else np.zeros((256, 4))
        np.savetxt(tmp_path / name, data, fmt="%.3f", delimiter="\t")

    table = trends.compute_trends(io.list_snapshots(tmp_path), test=2, workers=1)

    assert list(table["file_index"]) == [0, 1, 2]
    assert list(table["flatline"]) == [False, False, True]
    assert {"b1_s0_rms", "b4_s0_kurtosis", "b3_s0_peak"} <= set(table.columns)


def test_bearing_trend_takes_larger_sensor_value():
    table = pd.DataFrame({"b3_s0_rms": [1.0, 4.0], "b3_s1_rms": [2.0, 3.0]})
    assert list(trends.bearing_trend(table, 3, "rms")) == [2.0, 4.0]
    with pytest.raises(KeyError):
        trends.bearing_trend(table, 1, "rms")


def test_first_sustained_exceedance_finds_step_and_ignores_spike():
    values = np.ones(300) + np.random.default_rng(2).normal(scale=0.01, size=300)
    values[120] = 5.0  # single outlier: no lasting rise
    values[200:] += 1.0  # lasting rise from position 200
    series = pd.Series(values)

    onset = trends.first_sustained_exceedance(series, reference=slice(0, 100), smooth=5, sustain=5)

    # A trailing median of 5 crosses the band once 3 of the 5 values are high.
    assert onset == 202


def test_first_sustained_exceedance_returns_none_without_change():
    series = pd.Series(np.random.default_rng(3).normal(size=500))
    assert trends.first_sustained_exceedance(series, reference=slice(0, 200)) is None
