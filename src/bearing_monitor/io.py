"""Loading of raw IMS bearing vibration snapshots.

One snapshot is one ASCII file: one row per sample, one whitespace-separated
column per accelerometer channel. The file name is the recording timestamp,
e.g. ``2003.10.22.12.06.24``.

File format, samples per file and channel counts were verified against the
files on 2026-11-27 (see ``data/README.md``). The sampling rate is the
documented 20 kHz by project decision, although the signals point to 20.48 kHz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

#: Nominal sampling rate stated in the dataset readme.
#: ASSUMPTION: 20 480 samples are described as a "1-second" snapshot, which
#: would imply 20.48 kHz, and the outer race fault line of test 2 also fits
#: 20.48 kHz better (data/README.md). Decision (2026-11-28): use the
#: documented 20 kHz.
SAMPLING_RATE_HZ = 20_000.0
#: Number of samples per snapshot (verified for every file).
SAMPLES_PER_SNAPSHOT = 20_480
#: Shaft speed of the test rig in revolutions per minute.
SHAFT_SPEED_RPM = 2000.0

TIMESTAMP_FORMAT = "%Y.%m.%d.%H.%M.%S"


@dataclass(frozen=True)
class TestConfig:
    """Channel layout of one run-to-failure test."""

    name: str
    n_channels: int
    #: Maps bearing number (1-4) to the zero-based column indices of its sensors.
    bearing_channels: dict[int, tuple[int, ...]]


#: Channel layouts from the readme; channel counts verified for every file.
#: Note: ``3rd_test.rar`` extracts to a folder named ``4th_test/txt``.
TEST_CONFIGS: dict[int, TestConfig] = {
    1: TestConfig("1st_test", 8, {1: (0, 1), 2: (2, 3), 3: (4, 5), 4: (6, 7)}),
    2: TestConfig("2nd_test", 4, {1: (0,), 2: (1,), 3: (2,), 4: (3,)}),
    3: TestConfig("3rd_test", 4, {1: (0,), 2: (1,), 3: (2,), 4: (3,)}),
}


def parse_timestamp(path: str | Path) -> datetime:
    """Return the recording time encoded in a snapshot file name."""
    name = Path(path).name
    try:
        return datetime.strptime(name, TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"{name!r} is not a snapshot file name (expected YYYY.MM.DD.HH.MM.SS)"
        ) from exc


def list_snapshots(test_dir: str | Path) -> pd.Series:
    """List all snapshot files of one test in chronological order.

    Files whose names are not timestamps (e.g. a readme) are skipped.

    Returns
    -------
    pandas.Series
        File paths indexed by a sorted ``DatetimeIndex`` named ``timestamp``.
    """
    test_dir = Path(test_dir)
    if not test_dir.is_dir():
        raise FileNotFoundError(f"Test directory not found: {test_dir}")

    found: dict[datetime, Path] = {}
    for path in test_dir.iterdir():
        if not path.is_file():
            continue
        try:
            found[parse_timestamp(path)] = path
        except ValueError:
            continue
    if not found:
        raise FileNotFoundError(f"No snapshot files found in {test_dir}")

    series = pd.Series(found, name="path").sort_index()
    series.index = pd.DatetimeIndex(series.index, name="timestamp")
    return series


def load_snapshot(path: str | Path, n_channels: int | None = None) -> np.ndarray:
    """Load one snapshot file.

    Parameters
    ----------
    path
        Snapshot file.
    n_channels
        Expected number of channels. If given, a mismatch raises ``ValueError``
        instead of silently returning data in an unexpected layout.

    Returns
    -------
    numpy.ndarray
        Array of shape ``(n_samples, n_channels)``, dtype float64.
    """
    frame = pd.read_csv(path, sep=r"\s+", header=None, dtype=np.float64)
    data = frame.to_numpy()
    if n_channels is not None and data.shape[1] != n_channels:
        raise ValueError(f"{path}: expected {n_channels} channels, found {data.shape[1]}")
    return data


def bearing_signal(snapshot: np.ndarray, test: int, bearing: int, sensor: int = 0) -> np.ndarray:
    """Select the 1-D signal of one bearing from a loaded snapshot.

    ``sensor`` picks between the two accelerometers per bearing in test 1 and
    must be 0 for tests 2 and 3.
    """
    config = TEST_CONFIGS[test]
    if snapshot.shape[1] != config.n_channels:
        raise ValueError(
            f"Snapshot has {snapshot.shape[1]} channels, test {test} expects {config.n_channels}"
        )
    channels = config.bearing_channels[bearing]
    if not 0 <= sensor < len(channels):
        raise ValueError(f"Test {test}, bearing {bearing} has {len(channels)} sensor(s)")
    return snapshot[:, channels[sensor]]


def amplitude_spectrum(
    signal: np.ndarray, sampling_rate_hz: float = SAMPLING_RATE_HZ
) -> tuple[np.ndarray, np.ndarray]:
    """Single-sided amplitude spectrum of a 1-D signal.

    The mean is removed first so the DC offset of the sensor does not dominate.
    A sine of amplitude ``A`` at a bin frequency yields a peak of height ``A``.
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = signal.size
    spectrum = np.abs(np.fft.rfft(signal - signal.mean())) * 2.0 / n
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate_hz)
    return freqs, spectrum


def find_test_dirs(root: str | Path) -> list[Path]:
    """Find every directory below ``root`` that directly contains snapshot files.

    This avoids hard-coding the folder names of the extracted archive.
    """
    root = Path(root)
    dirs = set()
    for path in root.rglob("*"):
        if path.is_file():
            try:
                parse_timestamp(path)
            except ValueError:
                continue
            dirs.add(path.parent)
    return sorted(dirs)
