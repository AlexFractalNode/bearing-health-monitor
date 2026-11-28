"""Tests for the snapshot loader, using small synthetic files only."""

from datetime import datetime

import numpy as np
import pytest

from bearing_monitor import io


def write_snapshot(path, data):
    # Same layout as the dataset files: tab-separated ASCII, one row per sample.
    np.savetxt(path, data, fmt="%.3f", delimiter="\t")


def test_parse_timestamp():
    assert io.parse_timestamp("x/2003.10.22.12.06.24") == datetime(2003, 10, 22, 12, 6, 24)


def test_parse_timestamp_rejects_other_names():
    with pytest.raises(ValueError):
        io.parse_timestamp("readme.txt")


def test_list_snapshots_is_chronological_and_skips_other_files(tmp_path):
    for name in ["2004.02.12.10.52.39", "2004.02.12.10.32.39", "2004.02.12.10.42.39"]:
        write_snapshot(tmp_path / name, np.zeros((4, 4)))
    (tmp_path / "notes.txt").write_text("not a snapshot")

    snapshots = io.list_snapshots(tmp_path)

    assert len(snapshots) == 3
    assert snapshots.index.is_monotonic_increasing
    assert snapshots.iloc[0].name == "2004.02.12.10.32.39"


def test_list_snapshots_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        io.list_snapshots(tmp_path / "missing")


def test_load_snapshot_roundtrip(tmp_path):
    data = np.random.default_rng(0).normal(size=(100, 8)).round(3)
    path = tmp_path / "2003.10.22.12.06.24"
    write_snapshot(path, data)

    loaded = io.load_snapshot(path, n_channels=8)

    assert loaded.shape == (100, 8)
    np.testing.assert_allclose(loaded, data)


def test_load_snapshot_channel_mismatch(tmp_path):
    path = tmp_path / "2004.02.12.10.32.39"
    write_snapshot(path, np.zeros((10, 4)))
    with pytest.raises(ValueError):
        io.load_snapshot(path, n_channels=8)


def test_bearing_signal_selects_documented_channels():
    snapshot = np.tile(np.arange(8.0), (5, 1))
    assert io.bearing_signal(snapshot, test=1, bearing=3, sensor=1)[0] == 5.0
    assert io.bearing_signal(snapshot[:, :4], test=2, bearing=3)[0] == 2.0
    with pytest.raises(ValueError):
        io.bearing_signal(snapshot[:, :4], test=2, bearing=3, sensor=1)


def test_amplitude_spectrum_recovers_sine():
    fs, n = 20_000.0, 20_000
    t = np.arange(n) / fs
    signal = 0.5 + 2.0 * np.sin(2 * np.pi * 1000.0 * t)

    freqs, spectrum = io.amplitude_spectrum(signal, fs)

    peak = spectrum.argmax()
    assert freqs[peak] == pytest.approx(1000.0)
    assert spectrum[peak] == pytest.approx(2.0, rel=1e-6)
    assert spectrum[0] == pytest.approx(0.0, abs=1e-9)


def test_find_test_dirs(tmp_path):
    first = tmp_path / "a" / "1st_test"
    second = tmp_path / "2nd_test"
    for folder in (first, second):
        folder.mkdir(parents=True)
        write_snapshot(folder / "2004.02.12.10.32.39", np.zeros((2, 4)))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.txt").write_text("x")

    assert io.find_test_dirs(tmp_path) == sorted([first, second])
