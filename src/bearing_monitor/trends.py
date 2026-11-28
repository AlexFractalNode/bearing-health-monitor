"""Per-snapshot summary statistics for the phase 1 exploration.

Every snapshot of a test is reduced to a few numbers per channel (RMS,
kurtosis, peak), giving one time series per bearing over the whole run. These
trends are only used to look at the data. They are computed per snapshot,
never fitted on anything, so they cannot leak information across time.
The full, tested feature set follows in ``features.py`` (phase 2).
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from bearing_monitor import io

#: A snapshot whose RMS is below this on every channel is a flat line (sensor
#: or DAQ already off, see data/README.md). Healthy snapshots have RMS > 0.05.
FLATLINE_RMS = 0.02

STATISTICS = ("rms", "kurtosis", "peak")


def snapshot_statistics(signal: np.ndarray) -> dict[str, float]:
    """Summary statistics of one 1-D signal.

    Returns
    -------
    dict
        ``rms``: root mean square of the raw signal (DC offset included),
        ``kurtosis``: Pearson kurtosis (3 for a Gaussian signal, about 1.5 for
        a sine), ``peak``: largest absolute value.
    """
    signal = np.asarray(signal, dtype=np.float64)
    return {
        "rms": float(np.sqrt(np.mean(signal**2))),
        "kurtosis": float(stats.kurtosis(signal, fisher=False)),
        "peak": float(np.max(np.abs(signal))),
    }


def _snapshot_row(args: tuple[Path, int]) -> dict[str, float]:
    path, test = args
    config = io.TEST_CONFIGS[test]
    snapshot = io.load_snapshot(path, n_channels=config.n_channels)
    row: dict[str, float] = {}
    for bearing, channels in config.bearing_channels.items():
        for sensor in range(len(channels)):
            values = snapshot_statistics(io.bearing_signal(snapshot, test, bearing, sensor))
            for name, value in values.items():
                row[f"b{bearing}_s{sensor}_{name}"] = value
    return row


def compute_trends(snapshots: pd.Series, test: int, workers: int | None = None) -> pd.DataFrame:
    """Compute :func:`snapshot_statistics` for every snapshot and channel of one test.

    Parameters
    ----------
    snapshots
        Output of :func:`bearing_monitor.io.list_snapshots`.
    test
        Test number (1, 2 or 3), selects the channel layout.
    workers
        Number of worker processes; ``None`` uses all CPUs, ``1`` runs serially.

    Returns
    -------
    pandas.DataFrame
        One row per snapshot, indexed by timestamp. Columns ``file_index``
        (0-based position in the run), ``flatline`` and one column per
        ``b{bearing}_s{sensor}_{statistic}``.
    """
    jobs: Iterable[tuple[Path, int]] = [(Path(p), test) for p in snapshots]
    if workers == 1:
        rows = [_snapshot_row(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_snapshot_row, jobs, chunksize=16))

    trends = pd.DataFrame(rows, index=snapshots.index)
    rms_columns = [c for c in trends.columns if c.endswith("_rms")]
    trends.insert(0, "flatline", (trends[rms_columns] < FLATLINE_RMS).all(axis=1))
    trends.insert(0, "file_index", np.arange(len(trends)))
    return trends


def bearing_trend(trends: pd.DataFrame, bearing: int, statistic: str) -> pd.Series:
    """One statistic of one bearing; for two sensors (test 1) the larger value per snapshot."""
    columns = [c for c in trends.columns if c.startswith(f"b{bearing}_") and c.endswith(statistic)]
    if not columns:
        raise KeyError(f"No column for bearing {bearing}, statistic {statistic!r}")
    return trends[columns].max(axis=1).rename(f"b{bearing}_{statistic}")


def first_sustained_exceedance(
    values: pd.Series,
    reference: slice,
    k: float = 6.0,
    smooth: int = 6,
    sustain: int = 6,
) -> int | None:
    """Position of the first lasting rise above a healthy reference band.

    A descriptive rule for the exploration, not the anomaly detector of phase 3.
    The band is ``mean + k * std`` of ``values`` in the ``reference`` positions,
    i.e. the early part of the run only. The series is smoothed with a trailing
    (causal) rolling median of ``smooth`` snapshots, and the onset is the first
    position from which the smoothed value stays above the band for ``sustain``
    consecutive snapshots.

    Returns
    -------
    int or None
        0-based position in ``values``, or ``None`` if the band is never left.
    """
    ref = values.iloc[reference]
    limit = ref.mean() + k * ref.std()
    smoothed = values.rolling(smooth, min_periods=1).median().to_numpy()
    above = smoothed > limit
    above[: reference.stop or 0] = False
    run = 0
    for position, flag in enumerate(above):
        run = run + 1 if flag else 0
        if run == sustain:
            return position - sustain + 1
    return None
