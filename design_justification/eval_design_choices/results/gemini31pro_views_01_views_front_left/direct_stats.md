# Direct statistics (model-free)

- Source: `/Users/carrietan/Desktop/LabOS-Sim/benchmark_code/LabOS-Sim/design_justification/eval_design_choices/processed/gemini31pro_views_01_views_front_left/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.3   |               0.514 |              0.8 |            0.229 |       0.129 |    0.8   | 0.222 | 0.771 |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.238 |             nan     |            nan   |          nan     |       0.22  |    0.238 | 0.188 | 0.105 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.212 |             nan     |            nan   |          nan     |       0.245 |    0.213 | 0.112 | 0.107 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.238 |       0.138 |      0.4 | 0.205 | 0.357 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.238 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.238 |       0     |      0   | 0     | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.238 |       0.308 |      0.8 | 0.444 | 0.257 |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.238 |       0.286 |      0.2 | 0.235 | 0.071 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.238 |       0     |      0   | 0     | 0.014 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.238 |       0.667 |      0.4 | 0.5   | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.238 |       0.143 |      0.1 | 0.118 | 0.086 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.212 |       0.133 |      0.6 | 0.218 | 0.557 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.212 |       0     |      0   | 0     | 0.014 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.212 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.212 |       0.345 |      1   | 0.513 | 0.271 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.212 |       0.5   |      0.1 | 0.167 | 0.014 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.212 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_rack        |        10 |                    0.212 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | rack_flipped      |        10 |                    0.212 |     nan     |      0   | 0     | 0     |

For P1, the metric target is binary correctness (success/correct is positive).
For P2/P3, the target is one of eight classes: success or seven error types.
`accuracy` requires the single primary predicted type to exactly equal truth.
If a model returns multiple ordered types, only its first (most important)
type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.

Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's
own prevalence. For criterion-separated, prevalence-adjustable metrics with
uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).