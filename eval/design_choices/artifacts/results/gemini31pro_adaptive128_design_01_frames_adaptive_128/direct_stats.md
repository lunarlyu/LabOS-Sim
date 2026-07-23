# Direct statistics (model-free)

- Source: `/Users/luna/Documents/LabOS-sim/carrie-branching/design_choices/artifacts/processed/gemini31pro_adaptive128_design_01_frames_adaptive_128/detections_long.csv`
- Grouping: task x model
- Models: gemini_3_1_pro
- Subtypes: cap_open, other_failure, rack_flipped, tube_drop, tube_empty, vortex_off, wrong_orientation, wrong_rack

## Complete headline metrics

| task                                | model          | metric_target            |   n_samples |   accuracy |   balanced_accuracy |   success_recall |   failure_recall |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:-------------------------|------------:|-----------:|--------------------:|-----------------:|-----------------:|------------:|---------:|------:|------:|
| vortex_closed_binary                | gemini_3_1_pro | binary_correctness       |          80 |      0.25  |               0.443 |              0.7 |            0.186 |       0.109 |    0.7   | 0.189 | 0.814 |
| vortex_multilabel_classification    | gemini_3_1_pro | eight_class_primary_type |          80 |      0.162 |             nan     |            nan   |          nan     |       0.277 |    0.162 | 0.124 | 0.116 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | eight_class_primary_type |          80 |      0.162 |             nan     |            nan   |          nan     |       0.334 |    0.162 | 0.088 | 0.116 |

## Per-type precision / recall / F1 / FPR

| task                                | model          | type              |   n_truth |   overall_exact_accuracy |   precision |   recall |    f1 |   fpr |
|:------------------------------------|:---------------|:------------------|----------:|-------------------------:|------------:|---------:|------:|------:|
| vortex_multilabel_classification    | gemini_3_1_pro | success           |        10 |                    0.162 |       0.111 |      0.4 | 0.174 | 0.457 |
| vortex_multilabel_classification    | gemini_3_1_pro | cap_open          |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_drop         |        10 |                    0.162 |       1     |      0.1 | 0.182 | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | tube_empty        |        10 |                    0.162 |       0.25  |      0.5 | 0.333 | 0.214 |
| vortex_multilabel_classification    | gemini_3_1_pro | vortex_off        |        10 |                    0.162 |       0     |      0   | 0     | 0.014 |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_orientation |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_multilabel_classification    | gemini_3_1_pro | wrong_rack        |        10 |                    0.162 |       0.2   |      0.2 | 0.2   | 0.114 |
| vortex_multilabel_classification    | gemini_3_1_pro | rack_flipped      |        10 |                    0.162 |       0.1   |      0.1 | 0.1   | 0.129 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | success           |        10 |                    0.162 |       0.111 |      0.5 | 0.182 | 0.571 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | cap_open          |        10 |                    0.162 |       1     |      0.1 | 0.182 | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_drop         |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | tube_empty        |        10 |                    0.162 |       0.226 |      0.7 | 0.341 | 0.343 |
| vortex_open_detection_strict_parser | gemini_3_1_pro | vortex_off        |        10 |                    0.162 |     nan     |      0   | 0     | 0     |
| vortex_open_detection_strict_parser | gemini_3_1_pro | wrong_orientation |        10 |                    0.162 |       0     |      0   | 0     | 0.014 |
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