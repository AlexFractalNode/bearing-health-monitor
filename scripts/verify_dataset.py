"""Check the extracted IMS dataset against the documented facts.

Usage:
    python scripts/verify_dataset.py [data/raw] [--full]

For every folder that contains snapshot files it reports the number of files,
first and last timestamp, the recording intervals and, from a sample of files
(all files with ``--full``), the number of channels and samples per file.
Copy the output into ``data/README.md``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bearing_monitor import io


def describe(test_dir: Path, full: bool) -> None:
    """Print file count, time range, intervals and array shapes of one test folder."""
    snapshots = io.list_snapshots(test_dir)
    print(f"\n== {test_dir} ==")
    print(f"files:           {len(snapshots)}")
    print(f"first snapshot:  {snapshots.index[0]}")
    print(f"last snapshot:   {snapshots.index[-1]}")

    gaps = snapshots.index.to_series().diff().dropna().dt.total_seconds() / 60
    if not gaps.empty:
        counts = gaps.round().value_counts().sort_values(ascending=False)
        print("intervals (minutes: count), five most common:")
        for minutes, count in counts.head(5).items():
            print(f"  {minutes:8.0f}: {count}")
        print(f"longest gap:     {gaps.max():.0f} min after {gaps.idxmax()}")

    if full:
        sample = snapshots
    else:
        positions = np.unique(np.linspace(0, len(snapshots) - 1, 5).astype(int))
        sample = snapshots.iloc[positions]
    shapes: dict[tuple[int, int], int] = {}
    for path in sample:
        shape = io.load_snapshot(path).shape
        shapes[shape] = shapes.get(shape, 0) + 1
    scope = "all files" if full else f"{len(sample)} sampled files"
    print(f"shapes (samples, channels) in {scope}:")
    for shape, count in shapes.items():
        print(f"  {shape}: {count}")

    with open(snapshots.iloc[0], "rb") as handle:
        print(f"first line (raw): {handle.readline()!r}")


def main() -> None:
    """Parse the command line and describe every snapshot folder below the root."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default="data/raw", type=Path)
    parser.add_argument("--full", action="store_true", help="read every file (slow)")
    args = parser.parse_args()

    test_dirs = io.find_test_dirs(args.root)
    if not test_dirs:
        raise SystemExit(f"No snapshot files found below {args.root}. See data/README.md.")
    for test_dir in test_dirs:
        describe(test_dir, args.full)


if __name__ == "__main__":
    main()
