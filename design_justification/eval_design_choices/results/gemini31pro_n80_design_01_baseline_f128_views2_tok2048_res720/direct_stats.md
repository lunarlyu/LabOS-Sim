# Direct statistics (model-free)

- Source: `eval_design_choices/processed/gemini31pro_n80_design_01_baseline_f128_views2_tok2048_res720/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.525 |               0.557 |              0.6 |            0.514 |       0.15  |    0.6   | 0.24  | 0.486 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.162 |             nan     |            nan   |          nan     |       0.292 |    0.162 | 0.117 | 0.116 |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.138 |             nan     |            nan   |          nan     |       0.241 |    0.138 | 0.107 | 0.123 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.138 |       0.25  |      0.1 | 0.143 | 0.043 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.138 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.138 |       1     |      0.1 | 0.182 | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.138 |       0.102 |      0.5 | 0.169 | 0.629 |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.138 |       0     |      0   | 0     | 0.143 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.138 |       0     |      0   | 0     | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.138 |       0     |      0   | 0     | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.138 |       0.333 |      0.4 | 0.364 | 0.114 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.162 |       0.25  |      0.6 | 0.353 | 0.257 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.162 |       0.333 |      0.1 | 0.154 | 0.029 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.162 |       0.5   |      0.2 | 0.286 | 0.029 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.162 |       0.085 |      0.4 | 0.14  | 0.614 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_rack        |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | rack_flipped      |        10 |                    0.162 |     nan     |      0   | 0     | 0     |

For P1, the metric target is binary correctness (success/correct is positive).
For P2/P3, the target is one of eight classes: success or seven error types.
`accuracy` requires the single primary predicted type to exactly equal truth.
If a model returns multiple ordered types, only its first (most important)
type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.

Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's
own prevalence. For criterion-separated, prevalence-adjustable metrics with
uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).