# Detection-table summary (Stage 1)

- Schema detected: **failure_mode_classification**
- Models (M=1): gemini_3_1_pro
- Subtypes (C=8): cap_open, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack, rack_flipped, other_failure
- Items (I=80), detection cells (N=1920)
- Positive cells: 210 | negative cells: 1710
- Per-(model,sample) records: 240 total; dropped 0 parse-error and 0 ambiguous (kept: no ambiguous, no parse-error)

## Ground-truth prevalence per subtype

| subtype           |   n_present |   n_items |   prevalence |
|:------------------|------------:|----------:|-------------:|
| cap_open          |          10 |        80 |        0.125 |
| tube_drop         |          10 |        80 |        0.125 |
| tube_empty        |          10 |        80 |        0.125 |
| vortex_off        |          10 |        80 |        0.125 |
| wrong_orientation |          10 |        80 |        0.125 |
| wrong_rack        |          10 |        80 |        0.125 |
| rack_flipped      |          10 |        80 |        0.125 |
| other_failure     |           0 |        80 |        0     |

## Per-model recall / FPR (hard 0.5 flag)

| model          |   n_items |   hits |   false_alarms |    recall |       fpr |   mean_confidence |
|:---------------|----------:|-------:|---------------:|----------:|----------:|------------------:|
| gemini_3_1_pro |        80 |     17 |             62 | 0.0809524 | 0.0362573 |          0.964792 |

Feed `detections_long.csv` to `fit_sdt_irt.py` (Stage 2). Columns
`is_present` (ground truth) and `flagged` (model said present) are the SDT
positive/negative channels; `confidence` is decision-level, carried for a
future graded-response extension.