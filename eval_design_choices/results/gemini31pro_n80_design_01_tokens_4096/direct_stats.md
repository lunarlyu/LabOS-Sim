# Direct statistics (model-free)

- Source: `eval_design_choices/processed/gemini31pro_n80_design_01_tokens_4096/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.488 |               0.579 |              0.7 |            0.457 |       0.156 |    0.7   | 0.255 | 0.543 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.138 |             nan     |            nan   |          nan     |       0.128 |    0.138 | 0.076 | 0.12  |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.125 |             nan     |            nan   |          nan     |       0.197 |    0.125 | 0.084 | 0.125 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.125 |       0     |      0   | 0     | 0.057 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.125 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.125 |       1     |      0.1 | 0.182 | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.125 |       0.14  |      0.6 | 0.226 | 0.529 |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.125 |       0.071 |      0.1 | 0.083 | 0.186 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.125 |       0     |      0   | 0     | 0.043 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.125 |       0     |      0   | 0     | 0.043 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.125 |       0.167 |      0.2 | 0.182 | 0.143 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.138 |       0.2   |      0.5 | 0.286 | 0.286 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.138 |       0     |      0   | 0     | 0.014 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.138 |       0.333 |      0.1 | 0.154 | 0.029 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.138 |       0.104 |      0.5 | 0.172 | 0.614 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.138 |       0     |      0   | 0     | 0.014 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.138 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_rack        |        10 |                    0.138 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | rack_flipped      |        10 |                    0.138 |     nan     |      0   | 0     | 0     |

For P1, the metric target is binary correctness (success/correct is positive).
For P2/P3, the target is one of eight classes: success or seven error types.
`accuracy` requires the single primary predicted type to exactly equal truth.
If a model returns multiple ordered types, only its first (most important)
type is scored. Precision/recall/F1/FPR are macro per-type for P2/P3.

Note: these are hard-0.5 (thresholded-flag) statistics at the benchmark's
own prevalence. For criterion-separated, prevalence-adjustable metrics with
uncertainty, see the SDT-IRT fit (fit_sdt_irt.py).