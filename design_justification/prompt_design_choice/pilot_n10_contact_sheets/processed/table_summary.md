# Detection-table summary (Stage 1)

- Schema detected: **failure_mode_classification**
- Models (M=3): claude_opus_4_8, gemini_3_1_pro, qwen3_vl
- Subtypes (C=8): cap_open, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack, rack_flipped, other_failure
- Items (I=10), detection cells (N=4080)
- Positive cells: 355 | negative cells: 3725
- Per-(model,sample) records: 540 total; dropped 1 parse-error and 29 ambiguous (kept: no ambiguous, no parse-error)

## Ground-truth prevalence per subtype

| subtype           |   n_present |   n_items |   prevalence |
|:------------------|------------:|----------:|-------------:|
| cap_open          |           1 |        10 |          0.1 |
| tube_drop         |           1 |        10 |          0.1 |
| tube_empty        |           1 |        10 |          0.1 |
| vortex_off        |           1 |        10 |          0.1 |
| wrong_orientation |           1 |        10 |          0.1 |
| wrong_rack        |           1 |        10 |          0.1 |
| rack_flipped      |           1 |        10 |          0.1 |
| other_failure     |           0 |        10 |          0   |

## Per-model recall / FPR (hard 0.5 flag)

| model           |   n_items |   hits |   false_alarms |    recall |       fpr |   mean_confidence |
|:----------------|----------:|-------:|---------------:|----------:|----------:|------------------:|
| claude_opus_4_8 |        10 |      9 |            128 | 0.0873786 | 0.115837  |          0.638344 |
| gemini_3_1_pro  |        10 |      9 |             76 | 0.0714286 | 0.058193  |          0.946983 |
| qwen3_vl        |        10 |      2 |             17 | 0.015873  | 0.0129376 |          0.937222 |

Feed `detections_long.csv` to `fit_sdt_irt.py` (Stage 2). Columns
`is_present` (ground truth) and `flagged` (model said present) are the SDT
positive/negative channels; `confidence` is decision-level, carried for a
future graded-response extension.