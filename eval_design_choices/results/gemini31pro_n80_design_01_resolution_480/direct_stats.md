# Direct statistics (model-free)

- Source: `eval_design_choices/processed/gemini31pro_n80_design_01_resolution_480/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.438 |               0.464 |              0.5 |            0.429 |       0.111 |    0.5   | 0.182 | 0.571 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.125 |             nan     |            nan   |          nan     |       0.255 |    0.125 | 0.073 | 0.118 |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.075 |             nan     |            nan   |          nan     |       0.069 |    0.075 | 0.056 | 0.132 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.075 |       0     |      0   | 0     | 0.071 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.075 |       0     |      0   | 0     | 0.014 |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.075 |       0     |      0   | 0     | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.075 |       0.094 |      0.3 | 0.143 | 0.414 |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.075 |       0.071 |      0.1 | 0.083 | 0.186 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.075 |       0     |      0   | 0     | 0.043 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.075 |       0.333 |      0.1 | 0.154 | 0.029 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.075 |       0.05  |      0.1 | 0.067 | 0.271 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.125 |       0.158 |      0.3 | 0.207 | 0.229 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.125 |       0     |      0   | 0     | 0.057 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.125 |       1     |      0.1 | 0.182 | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.125 |       0.118 |      0.6 | 0.197 | 0.643 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.125 |       0     |      0   | 0     | 0.014 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.125 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_rack        |        10 |                    0.125 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | rack_flipped      |        10 |                    0.125 |     nan     |      0   | 0     | 0     |

For P1, the metric target is binary correctness (success/correct is positive).
For P2/P3, the target is one of eight classes: success or seven error types.
`accuracy` requires the single primary predicted type to exactly equal truth.
If a model returns multiple ordered types, only its first (most important)
type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.

Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's
own prevalence. For criterion-separated, prevalence-adjustable metrics with
uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).