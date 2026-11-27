# Data: NASA / IMS bearing run-to-failure dataset

Raw data is **not** part of this repository (`data/raw/` and `*.zip` are git-ignored).

## Download

| | |
|---|---|
| Catalog page | <https://catalog.data.gov/dataset/ims-bearings> (landing page <https://data.nasa.gov/dataset/ims-bearings>) |
| File | `IMS.zip` from <https://data.nasa.gov/docs/legacy/IMS.zip> |
| Publisher | NASA Prognostics Center of Excellence; data provided by the Center for Intelligent Maintenance Systems (IMS), University of Cincinnati |
| License | U.S. Government Works (<https://www.usa.gov/government-works>) |

1. Download `IMS.zip` and place it at `data/raw/IMS.zip`.
2. Extract it inside `data/raw/`, including any nested archives, until the snapshot files
   (named like `2003.10.22.12.06.24`) are plain files on disk. Folder names do not matter:
   the loader finds every folder that contains snapshot files.
3. Run `python scripts/verify_dataset.py data/raw` and compare the output with the table below.

## Verification status

> **Not yet verified against the files.** The download host `data.nasa.gov` was blocked in the
> environment this was written in (2026-11-27), so nothing below has been checked against the
> archive or its bundled readme. Each fact is marked with where it comes from.

Source key:

- **[C]** data.gov catalog entry (link above), read 2026-11-27.
- **[S]** secondary source quoting the bundled "Readme Document for IMS Bearing Data":
  <https://blog.csdn.net/weixin_39458727/article/details/136321308>, read 2026-11-27.
  Consistent with the project brief, but still second hand.
- **[U]** unconfirmed recollection from the literature, no source checked. Treat as a hint only.

### Test rig and file format

| Fact | Value | Source |
|---|---|---|
| Bearings | 4 Rexnord ZA-2115 double-row bearings on one shaft | [S] |
| Shaft speed | 2000 rpm (33.3 Hz), constant load | [S] |
| Snapshot | one file per snapshot, "1-second" recording | [S] |
| Samples per file | 20 480 | [S] |
| Sampling rate | 20 kHz | [S] |
| File format | ASCII, one row per sample, one column per channel | [S] |
| Column separator | tab | [U] |
| File name | recording timestamp `YYYY.MM.DD.HH.MM.SS` | [S] |
| Physical unit of the values | unknown | – |
| Download size and archive layout | unknown | – |

### The three tests

| | Test 1 | Test 2 | Test 3 | Source |
|---|---|---|---|---|
| Start | 2003-10-22 12:06:24 | 2004-02-12 10:32:39 | 2004-03-04 09:27:46 | [S] |
| End | 2003-11-25 23:39:56 | 2004-02-19 06:22:39 | 2004-04-04 19:01:57 | [S] |
| Files | 2 156 | 984 | 4 448 | [S] |
| Channels | 8 | 4 | 4 | [S] |
| Channel layout | bearing 1: ch 1–2, bearing 2: ch 3–4, bearing 3: ch 5–6, bearing 4: ch 7–8 | bearing n: ch n | bearing n: ch n | [S] |
| Interval | 10 min (first 43 files every 5 min) | 10 min | 10 min | [S] |
| Failure at end of test | bearing 3: inner race defect; bearing 4: roller element defect | bearing 1: outer race failure | bearing 3: outer race failure | [S] |

Tests were stopped when the debris collected on a magnetic plug exceeded a set level [S]. This is
the end of the run, not a precisely timed failure (see open points).

## Assumptions and open points

1. **Sampling rate: 20 kHz or 20.48 kHz?** 20 480 samples in a "1-second" snapshot implies
   20.48 kHz, while the readme states 20 kHz. The code uses the documented 20 kHz
   (`bearing_monitor.io.SAMPLING_RATE_HZ`). The difference shifts every frequency axis by 2.4 %,
   which matters for the fault frequencies in phase 2.
2. **File count of test 3.** Other users of the dataset report more files in the archive than the
   4 448 stated in the readme [U]. `verify_dataset.py` will show the real number.
3. **Which test-1 column belongs to which sensor direction** (two accelerometers per bearing) is
   not documented in the sources read so far.
4. **Gaps.** Larger gaps between timestamps reportedly mean the rig was restarted the next
   working day [S]. Elapsed time and operating time therefore differ.
5. **Failure time.** The sources only give the failed bearing and defect type per test, not a
   failure timestamp. How "failed" is defined is open point 1 of the project brief.

## Verified facts

To be filled in from the output of `scripts/verify_dataset.py` once the data is available.
