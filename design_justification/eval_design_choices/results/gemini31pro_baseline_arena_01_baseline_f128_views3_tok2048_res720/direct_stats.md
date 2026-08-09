# Direct statistics (model-free)

- Source: `/Users/carrietan/Desktop/LabOS-Sim/benchmark_code/LabOS-Sim/design_justification/eval_design_choices/processed/gemini31pro_baseline_arena_01_baseline_f128_views3_tok2048_res720/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.338 |               0.579 |              0.9 |            0.257 |       0.148 |    0.9   | 0.254 | 0.743 |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.188 |             nan     |            nan   |          nan     |       0.139 |    0.188 | 0.139 | 0.116 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.175 |             nan     |            nan   |          nan     |       0.446 |    0.175 | 0.107 | 0.112 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.188 |       0.091 |      0.3 | 0.14  | 0.429 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.188 |       0     |      0   | 0     | 0.014 |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.188 |       0     |      0   | 0     | 0.014 |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.188 |       0.333 |      0.7 | 0.452 | 0.2   |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.188 |       0     |      0   | 0     | 0.086 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.188 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.188 |       0.25  |      0.2 | 0.222 | 0.086 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.188 |       0.3   |      0.3 | 0.3   | 0.1   |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.175 |       0.13  |      0.6 | 0.214 | 0.571 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.175 |       1     |      0.2 | 0.333 | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.175 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.175 |       0.207 |      0.6 | 0.308 | 0.329 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.175 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.175 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_rack        |        10 |                    0.175 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | rack_flipped      |        10 |                    0.175 |     nan     |      0   | 0     | 0     |

For P1, the metric target is binary correctness (success/correct is positive).
For P2/P3, the target is one of eight classes: success or seven error types.
`accuracy` requires the single primary predicted type to exactly equal truth.
If a model returns multiple ordered types, only its first (most important)
type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.

Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's
own prevalence. For criterion-separated, prevalence-adjustable metrics with
uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).