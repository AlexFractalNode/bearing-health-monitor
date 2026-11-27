"""Project-wide paths and constants.

Dataset-specific facts (sampling rate, channel layout, failure times) are
deliberately not hard-coded here yet: they are verified against the IMS
readme and files during the phase 0 data check first.
"""

from pathlib import Path

#: Seed used wherever randomness is involved, for reproducible results.
RANDOM_SEED = 42

#: Repository root, resolved from this file (src/bearing_monitor/config.py).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
