# VLM Design-Choice Evaluation

We evaluated 80 samples from the first batch of Carrie's vortexing data: 10
successes and 10 examples from each of seven failure types.

## 1. Contact sheets vs. independent frames

| Frames | Representation | P1 binary | P1 balanced | P2 exact type | P3/P5 exact type | Cost |
|---:|---|---:|---:|---:|---:|---:|
| 128 | Contact sheet | 52.5% | **55.7%** | 13.8% | 16.3% | $4.88 |
| 128 | Independent frames | 27.5% | 50.0% | **30.0%** | **18.8%** | $409.44 |
| 256 | Contact sheet | 50.0% | 50.0% | 17.5% | 8.8% | $4.72 |
| 256 | Independent frames | 23.8% | 47.9% | **18.8%** | **17.5%** | $770.29 |

At 256 frames, the contact sheet becomes extremely large. Provider-side
rescaling or compression may reduce each tile's effective resolution, explaining
the lack of consistent benefit.

**Decision: use independent frames.**

## 2. 720 vs. 480 px

This comparison uses 128 independent frames/view.

| Resolution | P1 binary | P1 balanced | P2 exact | P3/P5 exact | Cost |
|---:|---:|---:|---:|---:|---:|
| 720 px | 27.5% | **50.0%** | **30.0%** | **18.8%** | **$409.44** |
| 480 px | **30.0%** | 47.1% | 20.0% | 11.3% | $413.51 |

At 480 px, the model reports **empty tube** more often, including for clips with
other primary labels. This contributes to the apparent P1 gain.

**Decision: use 720 px.**

## 3. 2,048 vs. 4,096 output tokens

This comparison uses 128-frame contact sheets.

| Token limit | P1 binary | P1 balanced | P2 exact | P3/P5 exact | Cost |
|---:|---:|---:|---:|---:|---:|
| 2,048 | **52.5%** | 55.7% | **13.8%** | **16.3%** | $4.88 |
| 4,096 | 48.8% | **57.9%** | 12.5% | 13.8% | **$4.75** |

Nearly all successful 2,048-token calls ended with `finish_reason=stop`, so
4,096 tokens provide no consistent benefit.

**Decision: use 2,048 output tokens.**

## 4. Independent-frame sampling

Fixed 128 and fixed 256 always emit the configured number of frames. Adaptive
128/256 use all decoded frames below their respective cap. Hybrid uses the
source length below 128, 128 frames for source lengths 128--255, and 256 frames
for source lengths at least 256.

| Setting | P1 binary | P1 balanced | P2 exact | P3/P5 exact | Completed cost |
|---|---:|---:|---:|---:|---:|
| Fixed 128 | **27.5%** | 50.0% | **30.0%** | 18.8% | **$409.44** |
| Fixed 256 | 23.8% | 47.9% | 18.8% | 17.5% | $770.29 |
| Adaptive 256 | 22.5% | 47.1% | 21.3% | 13.8% | $690.29 |
| Hybrid | 26.3% | **53.6%** | 16.3% | **20.0%** | $550.97 |
| Adaptive 128 | 25.0% | 44.3% | 16.3% | 16.3% | $411.86 |

### 4.1 Results by source length

Source length is the minimum decoded frame count across front, left, and right.

| Source length | Prompt | Fixed 128 | Fixed 256 | Adaptive 256 | Hybrid | Adaptive 128 |
|---|---|---:|---:|---:|---:|---:|
| <128, n=4 | P1 | 1/4 | 0/4 | **3/4** | 2/4 | 1/4 |
|  | P2 exact | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
|  | P3/P5 exact | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| 128--255, n=46 | P1 | **14/46** | 9/46 | 7/46 | 10/46 | 10/46 |
|  | P2 exact | **16/46** | 9/46 | 8/46 | 10/46 | 6/46 |
|  | P3/P5 exact | 9/46 | 7/46 | 5/46 | **10/46** | 7/46 |
| >=256, n=30 | P1 | 7/30 | **10/30** | 8/30 | 9/30 | 9/30 |
|  | P2 exact | 8/30 | 6/30 | **9/30** | 3/30 | 7/30 |
|  | P3/P5 exact | 6/30 | **7/30** | 6/30 | 6/30 | 6/30 |

### 4.2 Same inputs show that temperature 0 is not deterministic

Each block below contains the same samples and byte-identical images across the
listed settings. Scores are nevertheless different.

| Source-length group | Setting with identical input | Frames/view | Identical images per setting | P1 binary | P2 exact | P3/P5 exact |
|---|---|---:|---:|---:|---:|---:|
| <128, n=4 | Adaptive 128 | Original | 1,218 | 1/4 | 0/4 | 0/4 |
|  | Adaptive 256 | Original | 1,218 | 3/4 | 0/4 | 0/4 |
|  | Hybrid | Original | 1,218 | 2/4 | 0/4 | 0/4 |
| 128--255, n=46 | Fixed 128 | 128 | 17,664 | 14/46 | 16/46 | 9/46 |
|  | Adaptive 128 | 128 | 17,664 | 10/46 | 6/46 | 7/46 |
|  | Hybrid | 128 | 17,664 | 10/46 | 10/46 | 10/46 |
| >=256, n=30 | Fixed 128 | 128 | 11,520 | 7/30 | 8/30 | 6/30 |
|  | Adaptive 128 | 128 | 11,520 | 9/30 | 7/30 | 6/30 |
| >=256, n=30 | Fixed 256 | 256 | 23,040 | 10/30 | 6/30 | 7/30 |
|  | Adaptive 256 | 256 | 23,040 | 8/30 | 9/30 | 6/30 |
|  | Hybrid | 256 | 23,040 | 9/30 | 3/30 | 6/30 |

Different accuracies from the same images, samples, prompts, and model settings
show that temperature 0 is not deterministic through OpenRouter; within-block
differences are run-to-run variation, not sampler effects. Fixed 128 has the
lowest independent-frame cost and the highest overall P2 exact accuracy, while
no alternative improves consistently across prompts, so we select **fixed 128
frames/view**.

## Notes

- **P1 accuracy:** overall binary success/failure accuracy.
- **P1 balanced:** mean of success recall and failure recall.
- **P2 exact:** exact primary-type accuracy when the VLM is given the failure
  taxonomy; the prediction must match one of eight classes (success or seven
  failure types).
- **P3/P5 exact:** exact primary-type accuracy when P3 detects errors without
  seeing the taxonomy and P5 maps its description to the same eight classes.
- Evaluations use **front + left + right**. `front_lower` is stored for dataset
  compatibility but is not sent to the VLM.
- Costs include all three prompts, the P5 parser, and retries with reported usage.
