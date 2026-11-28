"""Tests for the phase 2 features, using synthetic signals with known answers."""

import numpy as np
import pytest

from bearing_monitor import features, io

FS = io.SAMPLING_RATE_HZ
N = io.SAMPLES_PER_SNAPSHOT
T = np.arange(N) / FS
#: Frequency resolution of one snapshot; test tones sit on exact bins to avoid leakage.
DF = FS / N


def test_fault_frequencies_of_the_za_2115_at_2000_rpm():
    f = features.ZA_2115.fault_frequencies(2000 / 60)

    # Values quoted in the IMS literature (Qiu et al. 2006).
    assert f["bpfo"] == pytest.approx(236.4, abs=0.1)
    assert f["bpfi"] == pytest.approx(296.9, abs=0.1)
    assert f["bsf"] == pytest.approx(139.9, abs=0.1)
    assert f["ftf"] == pytest.approx(14.8, abs=0.1)
    # Kinematic identity: BPFO + BPFI = n * shaft frequency.
    assert f["bpfo"] + f["bpfi"] == pytest.approx(16 * 2000 / 60)


def test_time_features_of_a_sine_with_offset():
    amplitude, offset = 2.0, 0.5
    x = offset + amplitude * np.sin(2 * np.pi * 50 * DF * T)  # 50 full periods

    result = features.time_features(x)

    assert result["std"] == pytest.approx(amplitude / np.sqrt(2), rel=1e-4)
    assert result["rms"] == pytest.approx(np.sqrt(offset**2 + amplitude**2 / 2), rel=1e-4)
    assert result["kurtosis"] == pytest.approx(1.5, rel=1e-3)
    assert result["skewness"] == pytest.approx(0.0, abs=1e-6)
    assert result["crest"] == pytest.approx(np.sqrt(2), rel=1e-4)
    assert result["p2p"] == pytest.approx(2 * amplitude, rel=1e-4)


def test_impulses_raise_kurtosis_crest_and_skewness():
    noise = np.random.default_rng(0).normal(size=N)
    impulsive = noise.copy()
    impulsive[::500] += 12.0

    base, spiky = features.time_features(noise), features.time_features(impulsive)

    assert base["kurtosis"] == pytest.approx(3.0, abs=0.15)
    assert spiky["kurtosis"] > 3 * base["kurtosis"]
    assert spiky["crest"] > base["crest"]
    assert spiky["skewness"] > 1.0


def test_constant_signal_gives_zeros_instead_of_nan():
    result = features.time_features(np.ones(100))
    assert result["crest"] == result["kurtosis"] == result["skewness"] == 0.0


def test_band_power_of_a_sine_lands_in_its_band_and_sums_to_the_variance():
    amplitude = 3.0
    x = amplitude * np.sin(2 * np.pi * 2_500.0 * T)

    result = features.frequency_features(x)
    bands = np.array([result[name] for name in features.BAND_FEATURES])

    assert np.argmax(bands) == 2  # band_2_3k
    assert result["band_2_3k"] / bands.sum() > 0.99
    assert bands.sum() == pytest.approx(amplitude**2 / 2, rel=0.01)  # Parseval
    assert result["centroid"] == pytest.approx(2_500.0, rel=0.01)


def test_band_power_of_white_noise_is_flat_and_centroid_is_mid_band():
    x = np.random.default_rng(1).normal(scale=2.0, size=N)

    result = features.frequency_features(x)
    bands = np.array([result[name] for name in features.BAND_FEATURES])

    assert bands.sum() == pytest.approx(4.0, rel=0.03)
    assert bands == pytest.approx(np.full(10, 0.4), rel=0.15)
    assert result["centroid"] == pytest.approx(FS / 4, rel=0.03)


def _amplitude_modulated(modulation_hz: float, carrier_hz: float = 4_000.0) -> np.ndarray:
    """Carrier at a 'resonance' whose amplitude pulses at ``modulation_hz``."""
    return (1.0 + 0.8 * np.cos(2 * np.pi * modulation_hz * T)) * np.sin(2 * np.pi * carrier_hz * T)


def test_envelope_spectrum_recovers_the_modulation_frequency():
    f_mod = 242 * DF  # 236.3 Hz, on a frequency bin
    freqs, amplitude = features.envelope_spectrum(_amplitude_modulated(f_mod))

    assert freqs[np.argmax(amplitude)] == pytest.approx(f_mod)
    # Envelope 1 + 0.8 cos(...) has a line of height 0.8 at the modulation frequency.
    assert amplitude.max() == pytest.approx(0.8, rel=0.05)


@pytest.mark.parametrize("fault", ["bpfo", "bpfi", "bsf"])
def test_envelope_features_point_to_the_simulated_fault(fault):
    f0 = features.FAULT_FREQUENCIES_HZ[fault]
    x = _amplitude_modulated(f0)

    result = features.envelope_features(x)
    ratios = {name: result[f"env_{name}_ratio"] for name in features.FAULT_FREQUENCIES_HZ}

    assert max(ratios, key=ratios.get) == fault
    assert ratios[fault] > 0.9


def test_envelope_window_covers_lines_shifted_by_the_sampling_rate_question():
    # If the true rate is 20.48 kHz but 20 kHz is assumed, lines appear 2.34 % low.
    shifted = features.FAULT_FREQUENCIES_HZ["bpfo"] * 20_000 / 20_480
    result = features.envelope_features(_amplitude_modulated(shifted))
    assert result["env_bpfo_ratio"] > 0.9


def test_impulse_train_through_a_resonance_shows_up_at_bpfi():
    """Closer to a real defect: decaying 3 kHz bursts at the BPFI rate plus noise."""
    rng = np.random.default_rng(2)
    f0 = features.FAULT_FREQUENCIES_HZ["bpfi"]
    burst_t = np.arange(200) / FS
    burst = np.exp(-burst_t * 1_500) * np.sin(2 * np.pi * 3_000 * burst_t)
    x = rng.normal(scale=0.2, size=N)
    for start in (np.arange(0, 1.0, 1 / f0) * FS).astype(int):
        stop = min(start + burst.size, N)
        x[start:stop] += burst[: stop - start]
    noise = features.envelope_features(rng.normal(scale=0.2, size=N))

    result = features.envelope_features(x)

    assert result["env_bpfi_ratio"] > 5 * result["env_bpfo_ratio"]
    assert result["env_bpfi_ratio"] > 5 * noise["env_bpfi_ratio"]


def test_signal_features_returns_every_feature_once():
    x = np.random.default_rng(3).normal(size=N)
    result = features.signal_features(x)
    assert tuple(result) == features.FEATURE_NAMES
    assert all(np.isfinite(v) for v in result.values())


def test_compute_features_layout_and_flatline(tmp_path):
    rng = np.random.default_rng(4)
    names = ["2003.10.22.12.06.24", "2003.10.22.12.16.24", "2003.10.22.12.26.24"]
    for i, name in enumerate(names):
        data = rng.normal(scale=0.1, size=(4096, 8)) if i < 2 else np.zeros((4096, 8))
        np.savetxt(tmp_path / name, data, fmt="%.3f", delimiter="\t")

    table = features.compute_features(io.list_snapshots(tmp_path), test=1, workers=1)

    assert list(table["file_index"]) == [0, 1, 2]
    assert list(table["flatline"]) == [False, False, True]
    assert table.shape[1] == 2 + 8 * len(features.FEATURE_NAMES)
    one = features.bearing_features(table, bearing=4, sensor=1)
    assert tuple(one.columns) == features.FEATURE_NAMES
    with pytest.raises(KeyError):
        features.bearing_features(table, bearing=4, sensor=2)
