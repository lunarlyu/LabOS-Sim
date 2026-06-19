# Full Benchmark Comparison, 1080px/30fps

Updated: 2026-06-17

This report uses the active full-suite runs after failed-row retry consolidation
and merges successful supplemental confidence retries when present. AUROC is
success-positive: `confidence` for predicted-success rows and `1 - confidence`
for predicted-failure rows.
Supplemental confidence retries recovered 13 rows, left 3 rows unresolved, and cost $0.297281.


## Binary Success/Failure

| Model | Accuracy | Balanced Acc. | Success Recall | Failure Recall | Success Precision | Success F1 | AUROC | Missing Conf. | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MiniMax | 73.9% | 48.5% | 0.0% | 96.9% | 0.0% | n/a | 0.543 | 0 | $0.974385 |
| Gemini Flash | 54.5% | 63.9% | 82.0% | 45.9% | 32.1% | 46.1% | 0.649 | 1 | $3.099853 |
| Gemini Pro | 58.4% | 65.4% | 78.7% | 52.0% | 33.8% | 47.3% | 0.653 | 0 | $4.014202 |
| Qwen | 54.1% | 67.6% | 93.4% | 41.8% | 33.3% | 49.1% | 0.687 | 0 | $2.265505 |

## Multiclass Failure Classification

| Model | Outcome Acc. | Exact Target Acc. | Expected Label Included | Success AUROC | Missing Conf. | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| MiniMax | 68.1% | 14.0% | 20.2% | 0.544 | 0 | $0.982039 |
| Gemini Flash | 56.4% | 37.4% | 39.3% | 0.650 | 2 | $3.481540 |
| Gemini Pro | 62.6% | 34.2% | 38.1% | 0.664 | 0 | $4.464586 |
| Qwen | 49.4% | 26.8% | 33.9% | 0.658 | 0 | $2.279913 |

## Binary Per-Category Accuracy

| Category | Model | Correct/N | Accuracy |
| --- | --- | --- | --- |
| success | MiniMax | 0/61 | 0.0% |
| success | Gemini Flash | 50/61 | 82.0% |
| success | Gemini Pro | 48/61 | 78.7% |
| success | Qwen | 57/61 | 93.4% |
| cap_open | MiniMax | 45/48 | 93.8% |
| cap_open | Gemini Flash | 22/48 | 45.8% |
| cap_open | Gemini Pro | 28/48 | 58.3% |
| cap_open | Qwen | 15/48 | 31.2% |
| tube_drop | MiniMax | 32/32 | 100.0% |
| tube_drop | Gemini Flash | 29/32 | 90.6% |
| tube_drop | Gemini Pro | 25/32 | 78.1% |
| tube_drop | Qwen | 27/32 | 84.4% |
| tube_empty | MiniMax | 11/11 | 100.0% |
| tube_empty | Gemini Flash | 5/11 | 45.5% |
| tube_empty | Gemini Pro | 4/11 | 36.4% |
| tube_empty | Qwen | 1/11 | 9.1% |
| vortex_off | MiniMax | 27/27 | 100.0% |
| vortex_off | Gemini Flash | 3/27 | 11.1% |
| vortex_off | Gemini Pro | 2/27 | 7.4% |
| vortex_off | Qwen | 3/27 | 11.1% |
| wrong_orientation | MiniMax | 12/12 | 100.0% |
| wrong_orientation | Gemini Flash | 2/12 | 16.7% |
| wrong_orientation | Gemini Pro | 4/12 | 33.3% |
| wrong_orientation | Qwen | 6/12 | 50.0% |
| wrong_rack | MiniMax | 30/32 | 93.8% |
| wrong_rack | Gemini Flash | 5/32 | 15.6% |
| wrong_rack | Gemini Pro | 15/32 | 46.9% |
| wrong_rack | Qwen | 6/32 | 18.8% |
| rack_flipped | MiniMax | 32/33 | 97.0% |
| rack_flipped | Gemini Flash | 24/33 | 72.7% |
| rack_flipped | Gemini Pro | 24/33 | 72.7% |
| rack_flipped | Qwen | 24/33 | 72.7% |

## Multiclass Per-Category Metrics

| Category | Model | Outcome Correct/N | Outcome Acc. | Exact Target Acc. | Expected Label Included |
| --- | --- | --- | --- | --- | --- |
| success | MiniMax | 5/61 | 8.2% | 8.2% | 8.2% |
| success | Gemini Flash | 43/61 | 70.5% | 70.5% | 70.5% |
| success | Gemini Pro | 44/61 | 72.1% | 72.1% | 72.1% |
| success | Qwen | 57/61 | 93.4% | 93.4% | 93.4% |
| cap_open | MiniMax | 32/48 | 66.7% | 2.1% | 4.2% |
| cap_open | Gemini Flash | 31/48 | 64.6% | 47.9% | 52.1% |
| cap_open | Gemini Pro | 30/48 | 62.5% | 25.0% | 27.1% |
| cap_open | Qwen | 13/48 | 27.1% | 10.4% | 10.4% |
| tube_drop | MiniMax | 32/32 | 100.0% | 21.9% | 62.5% |
| tube_drop | Gemini Flash | 27/32 | 84.4% | 62.5% | 65.6% |
| tube_drop | Gemini Pro | 29/32 | 90.6% | 37.5% | 43.8% |
| tube_drop | Qwen | 26/32 | 81.2% | 15.6% | 68.8% |
| tube_empty | MiniMax | 10/11 | 90.9% | 0.0% | 0.0% |
| tube_empty | Gemini Flash | 6/11 | 54.5% | 0.0% | 0.0% |
| tube_empty | Gemini Pro | 6/11 | 54.5% | 9.1% | 18.2% |
| tube_empty | Qwen | 1/11 | 9.1% | 0.0% | 0.0% |
| vortex_off | MiniMax | 25/27 | 92.6% | 85.2% | 92.6% |
| vortex_off | Gemini Flash | 6/27 | 22.2% | 11.1% | 11.1% |
| vortex_off | Gemini Pro | 5/27 | 18.5% | 11.1% | 14.8% |
| vortex_off | Qwen | 1/27 | 3.7% | 3.7% | 3.7% |
| wrong_orientation | MiniMax | 12/12 | 100.0% | 0.0% | 0.0% |
| wrong_orientation | Gemini Flash | 5/12 | 41.7% | 8.3% | 8.3% |
| wrong_orientation | Gemini Pro | 4/12 | 33.3% | 8.3% | 8.3% |
| wrong_orientation | Qwen | 0/12 | 0.0% | 0.0% | 0.0% |
| wrong_rack | MiniMax | 28/32 | 87.5% | 0.0% | 0.0% |
| wrong_rack | Gemini Flash | 6/32 | 18.8% | 6.2% | 6.2% |
| wrong_rack | Gemini Pro | 19/32 | 59.4% | 40.6% | 46.9% |
| wrong_rack | Qwen | 5/32 | 15.6% | 3.1% | 6.2% |
| rack_flipped | MiniMax | 30/33 | 90.9% | 0.0% | 0.0% |
| rack_flipped | Gemini Flash | 21/33 | 63.6% | 12.1% | 18.2% |
| rack_flipped | Gemini Pro | 24/33 | 72.7% | 6.1% | 15.2% |
| rack_flipped | Qwen | 24/33 | 72.7% | 0.0% | 0.0% |

## Charts

- `charts/binary_overall_metrics.svg`
- `charts/multiclass_overall_metrics.svg`
- `charts/binary_per_category_accuracy.svg`
- `charts/multiclass_per_category_expected_label.svg`
- `charts/cost_by_model.svg`
