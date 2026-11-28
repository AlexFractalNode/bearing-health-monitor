"""Per-snapshot features for the anomaly models (phase 2).

Every 1-D bearing signal of one snapshot is reduced to a fixed set of numbers:

* **Time domain:** RMS, standard deviation, kurtosis, skewness, crest factor,
  peak-to-peak.
* **Frequency domain:** signal power in ten 1 kHz bands of the Welch power
  spectral density, spectral centroid.
* **Envelope spectrum:** band-pass filter, Hilbert envelope, FFT; energy of the
  envelope spectrum around the bearing fault frequencies (BPFO, BPFI, BSF) and
  their first harmonics.

All features are computed from one snapshot alone. Nothing is fitted, so the
features cannot leak information across time; scalers and thresholds are fitted
on the training window in phase 3.

Envelope analysis in short: a local defect (a pit on a race or a roller) causes
a short impact every time a roller passes it. Each impact rings a structural
resonance in the kHz range. The raw spectrum shows this ringing, not the slow
impact rate. Band-passing around the resonance and taking the magnitude of the
analytic signal (Hilbert transform) recovers the *envelope* of the ringing,
which repeats at the impact rate. Its spectrum therefore has lines at the fault
frequency of the damaged component (e.g. BPFO for an outer race defect).
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal as sps
from scipy import stats

from bearing_monitor import io
from bearing_monitor.trends import FLATLINE_RMS


@dataclass(frozen=True)
class BearingGeometry:
    """Rolling-element bearing geometry needed for the fault frequencies."""

    n_rollers: int
    pitch_diameter: float
    roller_diameter: float
    contact_angle_deg: float

    def fault_frequencies(self, shaft_hz: float) -> dict[str, float]:
        """Kinematic fault frequencies in Hz for a given shaft frequency.

        Standard formulas for a stationary outer race and rotating inner race:

        * ``bpfo`` (ball pass frequency, outer race) ``= n/2 * fr * (1 - r)``
        * ``bpfi`` (ball pass frequency, inner race) ``= n/2 * fr * (1 + r)``
        * ``bsf`` (ball spin frequency) ``= D/(2d) * fr * (1 - r**2)``
        * ``ftf`` (fundamental train / cage frequency) ``= fr/2 * (1 - r)``

        with ``r = d/D * cos(contact angle)``.
        """
        r = self.roller_diameter / self.pitch_diameter * np.cos(np.deg2rad(self.contact_angle_deg))
        half_n = self.n_rollers / 2.0
        return {
            "bpfo": half_n * shaft_hz * (1.0 - r),
            "bpfi": half_n * shaft_hz * (1.0 + r),
            "bsf": self.pitch_diameter / (2.0 * self.roller_diameter) * shaft_hz * (1.0 - r**2),
            "ftf": shaft_hz / 2.0 * (1.0 - r),
        }


#: Rexnord ZA-2115 double-row bearing of the IMS rig. Values as quoted in the
#: IMS literature (Qiu et al. 2006, J. Sound Vib. 289, 1066-1090, which also
#: gives BPFO 236.4 Hz and BPFI 296.9 Hz at 2000 rpm). Not stated in the
#: dataset readme and not checked against a Rexnord datasheet.
ZA_2115 = BearingGeometry(
    n_rollers=16, pitch_diameter=2.815, roller_diameter=0.331, contact_angle_deg=15.17
)

SHAFT_HZ = io.SHAFT_SPEED_RPM / 60.0

#: Fault frequencies used for the envelope features (Hz, at 2000 rpm):
#: BPFO 236.4, BPFI 296.9, BSF 139.9.
FAULT_FREQUENCIES_HZ = {k: v for k, v in ZA_2115.fault_frequencies(SHAFT_HZ).items() if k != "ftf"}

#: Band-pass for the envelope, chosen a priori (not tuned on the data): it keeps
#: the kHz resonances excited by impacts and removes the shaft harmonics and
#: low-frequency structural vibration below 1 kHz.
ENVELOPE_BAND_HZ = (1_000.0, 9_000.0)
#: Harmonics of each fault frequency summed into one envelope feature.
ENVELOPE_HARMONICS = 3
#: Relative search window around each harmonic, ``(below, above)``. Asymmetric
#: on purpose: with the documented 20 kHz sampling rate the lines are expected
#: about 2.5 % *below* their theoretical value if the true rate is 20.48 kHz
#: (data/README.md). The window covers both cases and keeps the BPFI line
#: (296.9 Hz) and the second BSF harmonic (279.8 Hz) apart.
ENVELOPE_TOLERANCE = (0.04, 0.015)

#: Edges of the frequency bands of the Welch PSD, 0 to 10 kHz in 1 kHz steps.
BAND_EDGES_HZ = tuple(float(f) for f in np.arange(0, 10_001, 1_000))
#: Segment length of the Welch PSD (about 10 Hz resolution at 20 kHz).
WELCH_NPERSEG = 2048

TIME_FEATURES = ("rms", "std", "kurtosis", "skewness", "crest", "p2p")
BAND_FEATURES = tuple(
    f"band_{int(lo / 1000)}_{int(hi / 1000)}k"
    for lo, hi in zip(BAND_EDGES_HZ[:-1], BAND_EDGES_HZ[1:], strict=True)
)
ENVELOPE_FEATURES = tuple(
    f"env_{name}_{kind}" for name in FAULT_FREQUENCIES_HZ for kind in ("energy", "ratio")
)
FEATURE_NAMES = TIME_FEATURES + BAND_FEATURES + ("centroid",) + ENVELOPE_FEATURES


def time_features(signal: np.ndarray) -> dict[str, float]:
    """Time-domain statistics of one 1-D signal.

    Returns
    -------
    dict
        ``rms`` of the raw signal (DC offset included, as in phase 1), ``std``
        (RMS without the DC offset), Pearson ``kurtosis`` (3 for Gaussian
        noise), ``skewness``, ``crest`` factor (largest absolute deviation from
        the mean divided by ``std``) and peak-to-peak value ``p2p``. A constant
        signal gives zeros for the shape statistics instead of NaN.
    """
    x = np.asarray(signal, dtype=np.float64)
    centered = x - x.mean()
    std = float(np.sqrt(np.mean(centered**2)))
    if std == 0:
        # Constant signal: higher moments are undefined, report zeros instead of NaN.
        return {
            "rms": float(np.sqrt(np.mean(x**2))),
            "std": 0.0,
            "kurtosis": 0.0,
            "skewness": 0.0,
            "crest": 0.0,
            "p2p": 0.0,
        }
    return {
        "rms": float(np.sqrt(np.mean(x**2))),
        "std": std,
        "kurtosis": float(stats.kurtosis(x, fisher=False)),
        "skewness": float(stats.skew(x)),
        "crest": float(np.max(np.abs(centered)) / std),
        "p2p": float(np.ptp(x)),
    }


def welch_psd(
    signal: np.ndarray, sampling_rate_hz: float = io.SAMPLING_RATE_HZ
) -> tuple[np.ndarray, np.ndarray]:
    """One-sided Welch power spectral density (Hann window, 50 % overlap, mean removed)."""
    x = np.asarray(signal, dtype=np.float64)
    return sps.welch(x, fs=sampling_rate_hz, nperseg=min(WELCH_NPERSEG, x.size), detrend="constant")


def frequency_features(
    signal: np.ndarray, sampling_rate_hz: float = io.SAMPLING_RATE_HZ
) -> dict[str, float]:
    """Band powers and spectral centroid from the Welch PSD.

    Each ``band_*`` value is the PSD integrated over its band, i.e. the signal
    power (variance) in that band; summed over all bands it approximates the
    variance of the signal. ``centroid`` is the power-weighted mean frequency in Hz.
    """
    freqs, psd = welch_psd(signal, sampling_rate_hz)
    df = freqs[1] - freqs[0]
    result: dict[str, float] = {}
    edges = BAND_EDGES_HZ
    for name, lo, hi in zip(BAND_FEATURES, edges[:-1], edges[1:], strict=True):
        # Half-open bands [lo, hi); the last band also takes the Nyquist bin.
        mask = (freqs >= lo) & ((freqs < hi) | (hi == edges[-1]))
        result[name] = float(psd[mask].sum() * df)
    total = psd.sum()
    result["centroid"] = float((freqs * psd).sum() / total) if total > 0 else 0.0
    return result


def envelope_spectrum(
    signal: np.ndarray,
    sampling_rate_hz: float = io.SAMPLING_RATE_HZ,
    band_hz: tuple[float, float] = ENVELOPE_BAND_HZ,
) -> tuple[np.ndarray, np.ndarray]:
    """Amplitude spectrum of the Hilbert envelope of the band-passed signal.

    The signal is filtered with a 4th-order Butterworth band-pass (zero-phase,
    ``sosfiltfilt``), the envelope is the magnitude of the analytic signal, and
    its mean is removed before the FFT so that the DC line does not dominate.
    """
    x = np.asarray(signal, dtype=np.float64)
    sos = sps.butter(4, band_hz, btype="bandpass", fs=sampling_rate_hz, output="sos")
    filtered = sps.sosfiltfilt(sos, x - x.mean())
    envelope = np.abs(sps.hilbert(filtered))
    return io.amplitude_spectrum(envelope, sampling_rate_hz)


def envelope_features(
    signal: np.ndarray,
    sampling_rate_hz: float = io.SAMPLING_RATE_HZ,
    fault_frequencies_hz: dict[str, float] | None = None,
) -> dict[str, float]:
    """Envelope-spectrum energy around each bearing fault frequency.

    For every fault frequency ``f``, the squared envelope amplitudes in the
    windows around ``f, 2f, ..., ENVELOPE_HARMONICS * f`` are summed
    (``env_<fault>_energy``). ``env_<fault>_ratio`` divides this by the energy
    of the whole envelope spectrum from 10 Hz to 1 kHz, which makes it
    insensitive to the overall vibration level.
    """
    faults = FAULT_FREQUENCIES_HZ if fault_frequencies_hz is None else fault_frequencies_hz
    freqs, amplitude = envelope_spectrum(signal, sampling_rate_hz)
    power = amplitude**2
    total = power[(freqs >= 10.0) & (freqs <= 1_000.0)].sum()
    below, above = ENVELOPE_TOLERANCE
    result: dict[str, float] = {}
    for name, f0 in faults.items():
        mask = np.zeros_like(freqs, dtype=bool)
        for h in range(1, ENVELOPE_HARMONICS + 1):
            mask |= (freqs >= h * f0 * (1 - below)) & (freqs <= h * f0 * (1 + above))
        energy = float(power[mask].sum())
        result[f"env_{name}_energy"] = energy
        result[f"env_{name}_ratio"] = energy / total if total > 0 else 0.0
    return result


def signal_features(
    signal: np.ndarray, sampling_rate_hz: float = io.SAMPLING_RATE_HZ
) -> dict[str, float]:
    """All features of one 1-D signal, keyed by the names in :data:`FEATURE_NAMES`."""
    result = time_features(signal)
    result.update(frequency_features(signal, sampling_rate_hz))
    result.update(envelope_features(signal, sampling_rate_hz))
    return result


def _snapshot_row(args: tuple[Path, int]) -> dict[str, float]:
    path, test = args
    config = io.TEST_CONFIGS[test]
    snapshot = io.load_snapshot(path, n_channels=config.n_channels)
    row: dict[str, float] = {}
    for bearing, channels in config.bearing_channels.items():
        for sensor in range(len(channels)):
            values = signal_features(io.bearing_signal(snapshot, test, bearing, sensor))
            for name, value in values.items():
                row[f"b{bearing}_s{sensor}_{name}"] = value
    return row


def compute_features(snapshots: pd.Series, test: int, workers: int | None = None) -> pd.DataFrame:
    """Compute :func:`signal_features` for every snapshot and channel of one test.

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
        (0-based position in the run), ``flatline`` (sensor or DAQ already off,
        to be dropped before modelling) and one column per
        ``b{bearing}_s{sensor}_{feature}``.
    """
    jobs: Iterable[tuple[Path, int]] = [(Path(p), test) for p in snapshots]
    if workers == 1:
        rows = [_snapshot_row(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_snapshot_row, jobs, chunksize=16))

    table = pd.DataFrame(rows, index=snapshots.index)
    rms_columns = [c for c in table.columns if c.endswith("_rms")]
    table.insert(0, "flatline", (table[rms_columns] < FLATLINE_RMS).all(axis=1))
    table.insert(0, "file_index", np.arange(len(table)))
    return table


def bearing_features(table: pd.DataFrame, bearing: int, sensor: int = 0) -> pd.DataFrame:
    """Feature columns of one bearing and sensor, renamed to the plain feature names."""
    prefix = f"b{bearing}_s{sensor}_"
    columns = [c for c in table.columns if c.startswith(prefix)]
    if not columns:
        raise KeyError(f"No feature columns for bearing {bearing}, sensor {sensor}")
    return table[columns].rename(columns=lambda c: c[len(prefix) :])
