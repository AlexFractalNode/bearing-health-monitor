"""Compute the phase 2 feature table for all three IMS tests.

Usage::

    python scripts/compute_features.py data/raw [--out data/processed] [--workers N]

Writes ``features_test{1,2,3}.parquet`` (git-ignored): one row per snapshot, one
column per bearing, sensor and feature (see ``bearing_monitor.features``).
Flat-lined snapshots are kept but marked in the ``flatline`` column.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from bearing_monitor import features, io
from bearing_monitor.config import PROCESSED_DATA_DIR

#: Folder name of each test after extraction (3rd_test.rar extracts to 4th_test/txt).
TEST_FOLDERS = {1: "1st_test", 2: "2nd_test", 3: "4th_test"}


def find_test_dir(root: Path, test: int) -> Path:
    """Return the snapshot folder of one test below ``root``."""
    matches = [d for d in io.find_test_dirs(root) if TEST_FOLDERS[test] in d.parts]
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one folder for test {test} below {root}, got {matches}")
    return matches[0]


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="folder with the extracted IMS data")
    parser.add_argument("--out", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--tests", type=int, nargs="+", default=[1, 2, 3])
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for test in args.tests:
        start = time.perf_counter()
        snapshots = io.list_snapshots(find_test_dir(args.root, test))
        table = features.compute_features(snapshots, test, workers=args.workers)
        target = args.out / f"features_test{test}.parquet"
        table.to_parquet(target)
        print(
            f"test {test}: {len(table)} snapshots x {table.shape[1]} columns, "
            f"{int(table['flatline'].sum())} flat-lined, "
            f"{time.perf_counter() - start:.0f} s -> {target}"
        )


if __name__ == "__main__":
    main()
