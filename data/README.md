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
2. Extract it inside `data/raw/`, then extract the three nested **RAR** archives in
   `data/raw/IMS/` (for example `unar 1st_test.rar`, or 7-Zip on Windows) until the snapshot files
   (named like `2003.10.22.12.06.24`) are plain files on disk. Folder names do not matter:
   the loader finds every folder that contains snapshot files.
3. Run `python scripts/verify_dataset.py data/raw` and compare the output with the table below.

## Verification status

Checked on 2026-11-27 against `IMS.zip` downloaded from the link above and its bundled
"Readme Document for IMS Bearing Data.pdf", using `scripts/verify_dataset.py data/raw --full`
(every file read). Each fact is marked with its source:

- **[F]** verified against the files themselves.
- **[R]** stated in the bundled readme PDF (read directly, not second hand).
- **[A]** own analysis of the signals, see the note at the fact. Evidence, not proof.
- **[U]** from memory of the literature, no source checked. Treat as a hint only.

### Archive layout

| Fact | Value | Source |
|---|---|---|
| `IMS.zip` | 1 061 902 801 bytes (1.06 GB) | [F] |
| Contents of `IMS.zip` | folder `IMS/` with `1st_test.rar`, `2nd_test.rar`, `3rd_test.rar` and the readme PDF, plus a `__MACOSX/` folder with macOS metadata (can be deleted) | [F] |
| Nested archives | RAR, not ZIP. Python's `zipfile` cannot open them; use `unar`, `unrar`, 7-Zip or `bsdtar` | [F] |
| `1st_test.rar` | extracts to `1st_test/`, 2 156 files | [F] |
| `2nd_test.rar` | extracts to `2nd_test/`, 984 files | [F] |
| `3rd_test.rar` | extracts to **`4th_test/txt/`**, 6 324 files (the folder name is misleading, it is test 3) | [F] |
| Size on disk after extraction | about 6.2 GB (2.4 GB + 0.5 GB + 3.3 GB) | [F] |

The loader finds snapshot folders by file name, so the odd folder name does not matter, but
`find_test_dirs` returns them in the order `1st_test`, `2nd_test`, `4th_test/txt`.

### Test rig and file format

| Fact | Value | Source |
|---|---|---|
| Bearings | 4 Rexnord ZA-2115 double-row bearings on one shaft, force lubricated | [R] |
| Shaft speed and load | 2000 rpm (33.3 Hz) by an AC motor via rub belts; 6000 lbs radial load | [R] |
| Sensors | PCB 353B33 ICP accelerometers on the bearing housings; DAQ card NI 6062E | [R] |
| Snapshot | one file per snapshot, described as a "1-second" recording | [R] |
| Samples per file | 20 480 in every file of all three tests | [F] |
| Sampling rate | readme says 20 kHz; signal analysis points to 20.48 kHz (open point 1) | [R], [A] |
| File format | ASCII, one row per sample, one column per channel, no header | [F] |
| Column separator | tab (`\t`), lines end with CRLF (`\r\n`) | [F] |
| Number format | three decimals, e.g. `-0.022` | [F] |
| File name | recording timestamp `YYYY.MM.DD.HH.MM.SS` | [F] |
| Physical unit of the values | not stated in the readme. Last file of test 1 clips at exactly ±5.000 on channel 5, which suggests a ±5 V input range (raw volts) | [A] |

### The three tests

| | Test 1 | Test 2 | Test 3 | Source |
|---|---|---|---|---|
| First file | 2003-10-22 12:06:24 | 2004-02-12 10:32:39 | 2004-03-04 09:27:46 | [F] |
| Last file | 2003-11-25 23:39:56 | 2004-02-19 06:22:39 | **2004-04-18 02:42:55** | [F] |
| Files | 2 156 | 984 | **6 324** | [F] |
| Readme says | same | same | 4 448 files, ending 2004-04-04 19:01:57 | [R] |
| Channels | 8 | 4 | 4 | [F] |
| Channel layout | bearing 1: ch 1–2, bearing 2: ch 3–4, bearing 3: ch 5–6, bearing 4: ch 7–8 (x and y axis) | bearing n: ch n | bearing n: ch n | [R] |
| Interval | 10 min (1 962×), 5 min (148×), 24 gaps > 20 min, longest 6.2 days | 10 min, no gaps | 10 min, 4 gaps > 20 min (70 to 452 min) | [F] |
| Failure at end of test | bearing 3: inner race defect; bearing 4: roller element defect | bearing 1: outer race failure | bearing 3: outer race failure | [R] |
| Flat-lined files at the end | none | last 2 (2004-02-19 06:12:39 and 06:22:39) | last 1 (2004-04-18 02:42:55) | [F] |

## Findings that change the plan

1. **Test 3 has 1 876 more files than the readme says.** Files 1 to 4 448 match the readme
   exactly (file 4 448 is 2004-04-04 19:01:57). The recording then continues without a gap for
   another 13 days. The signal of bearing 3 (the failed one) stays flat up to file 4 448 (RMS about
   0.07) and only rises in the extra part: 0.08 on 2004-04-15, 0.19 on 04-17, 0.76 in the last live
   file on 04-18. The degradation is therefore **only visible in the files the readme does not
   mention**. "Failure = end of test" must use the end of the archive, not the readme date, or test
   3 has no failure in it at all. It is not documented why the readme stops early.
   **Decision (Alex, 2026-11-28):** test 3 uses all 6 324 files; its failure time is the last
   live file, 2004-04-18 02:32:55. The literature onset estimate for test 3 (Zhang et al. 2019,
   file index 2 367) lies inside the first 4 448 files and is kept only as a reference.
2. **Flat-lined last files.** The last two files of test 2 and the last file of test 3 contain
   only values of about zero (RMS < 0.02 on all channels): the sensors or the DAQ were already
   off. They are not vibration data and should be dropped before features are computed. The last
   live file is 2004-02-19 06:02:39 (test 2) and 2004-04-18 02:32:55 (test 3).
3. **Test 1 is not continuous.** It has 24 gaps longer than 20 minutes (up to 6.2 days, the
   "next working day" restarts in the readme), and 148 intervals of 5 minutes instead of the 43
   the readme mentions. Elapsed time and run time differ; time axes should either use the file
   index or the summed run time.

## Assumptions and open points

1. **Sampling rate: 20 kHz or 20.48 kHz?** The files have no time column, so the files alone
   cannot settle it. Evidence [A]: in the envelope spectrum of test 2, bearing 1 (outer race
   failure), averaged over files 700 to 900, the dominant line sits at bin 236 of 20 480. That is
   236.0 Hz at 20.48 kHz and 230.5 Hz at 20 kHz. The outer race fault frequency of the ZA-2115 at
   2000 rpm is usually quoted as about 236.4 Hz [U, Qiu et al. 2006]. This fits 20.48 kHz unless
   the belt drive slips by 2.5 %. The code still uses the documented 20 kHz
   (`bearing_monitor.io.SAMPLING_RATE_HZ`); the choice must be made before phase 2.
2. **Which test-1 column is x and which is y** is not stated beyond "two accelerometers for each
   bearing [x- and y-axes]" [R].
3. **Failure time.** The readme only gives the failed bearing and defect type per test, not a
   failure timestamp. See open point 1 of the project brief and finding 1 above.

## Verified facts

Output of `python scripts/verify_dataset.py data/raw --full` (2026-11-27), shortened:

```text
== data/raw/IMS/1st_test ==
files:           2156
first snapshot:  2003-10-22 12:06:24
last snapshot:   2003-11-25 23:39:56
intervals (minutes: count), five most common:
        10: 1962
         5: 148
         9: 5
         6: 4
         4: 4
longest gap:     8906 min after 2003-10-29 14:39:46
shapes (samples, channels) in all files:
  (20480, 8): 2156
first line (raw): b'-0.022\t-0.039\t-0.183\t-0.054\t-0.105\t-0.134\t-0.129\t-0.142\r\n'

== data/raw/IMS/2nd_test ==
files:           984
first snapshot:  2004-02-12 10:32:39
last snapshot:   2004-02-19 06:22:39
intervals (minutes: count), five most common:
        10: 983
longest gap:     10 min after 2004-02-12 10:42:39
shapes (samples, channels) in all files:
  (20480, 4): 984
first line (raw): b'-0.049\t-0.071\t-0.132\t-0.010\r\n'

== data/raw/IMS/4th_test/txt ==
files:           6324
first snapshot:  2004-03-04 09:27:46
last snapshot:   2004-04-18 02:42:55
intervals (minutes: count), five most common:
        10: 6315
         5: 2
       270: 1
         2: 1
       452: 1
longest gap:     452 min after 2004-03-19 10:37:17
shapes (samples, channels) in all files:
  (20480, 4): 6324
first line (raw): b'0.034\t0.264\t0.039\t-0.046\r\n'
```
