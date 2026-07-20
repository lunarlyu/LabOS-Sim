# VLM Design-Choice Evaluation

We evaluated 80 samples from the first batch of Carrie's vortexing data: 10
successes and 10 examples from each of seven failure types.

## 1. Contact sheets vs. independent frames

| Frames | Representation | P1 binary | P2 exact type | P3/P5 exact type | Cost |
|---:|---|---:|---:|---:|---:|
| 128 | Contact sheet | 52.5% | 13.8% | 16.3% | $4.88 |
| 128 | Independent frames | 27.5% | **30.0%** | **18.8%** | $409.44 |
| 256 | Contact sheet | 50.0% | 17.5% | 8.8% | $4.72 |
| 256 | Independent frames | 23.8% | **18.8%** | **17.5%** | $770.29 |

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

## 4. 128 vs. 256 independent frames

Adaptive 256 uses all decoded frames below 256 and uniformly samples 256 above
that limit.

| Setting | P1 binary | P1 balanced | P2 exact | P3/P5 exact | Completed cost |
|---|---:|---:|---:|---:|---:|
| Fixed 128 | **27.5%** | **50.0%** | **30.0%** | **18.8%** | **$409.44** |
| Fixed 256 | 23.8% | 47.9% | 18.8% | 17.5% | $770.29 |
| Adaptive 256 | 22.5% | 47.1% | 21.3% | 13.8% | $690.29 |

### 4.1 Fixed 256 and duplicated frames

Fifty clips have fewer than 256 source frames, so fixed 256 duplicates frames.

| Source length | n | Prompt | Fixed 128 | Fixed 256 |
|---|---:|---|---:|---:|
| <256 frames | 50 | P1 | **15/50 (30.0%)** | 9/50 (18.0%) |
| | | P2 exact | **16/50 (32.0%)** | 9/50 (18.0%) |
| | | P3/P5 | **9/50 (18.0%)** | 7/50 (14.0%) |
| >=256 frames | 30 | P1 | 7/30 (23.3%) | **10/30 (33.3%)** |
| | | P2 exact | **8/30 (26.7%)** | 6/30 (20.0%) |
| | | P3/P5 | 6/30 (20.0%) | **7/30 (23.3%)** |

Among clips with at least 256 genuine frames, P1 and P3/P5 improve slightly,
but P2 decreases.

### 4.2 Adaptive 256 drops most on the 128--255-frame group

| Source length | n | Prompt | Fixed 128 | Adaptive 256 |
|---|---:|---|---:|---:|
| <128 frames | 4 | P1 | 1/4 (25.0%) | **3/4 (75.0%)** |
| | | P2 exact | 0/4 (0.0%) | 0/4 (0.0%) |
| | | P3/P5 exact | 0/4 (0.0%) | 0/4 (0.0%) |
| 128--255 frames | 46 | P1 | **14/46 (30.4%)** | 7/46 (15.2%) |
| | | P2 exact | **16/46 (34.8%)** | 8/46 (17.4%) |
| | | P3/P5 exact | **9/46 (19.6%)** | 5/46 (10.9%) |
| >=256 frames | 30 | P1 | 7/30 (23.3%) | **8/30 (26.7%)** |
| | | P2 exact | 8/30 (26.7%) | **9/30 (30.0%)** |
| | | P3/P5 exact | 6/30 (20.0%) | 6/30 (20.0%) |

Possible explanations include dilution of brief failure cues by similar frames
and greater distance between corresponding moments across grouped views. The
128--255-frame group decreases on all three prompting paths.

### 4.3 Adaptive-256 success bias on P2

| P2 behavior | Fixed 128 | Adaptive 256 |
|---|---:|---:|
| Total predicted `success` | 29/80 | 39/80 |
| True successes correctly predicted | 5/10 | **9/10** |
| Failures mislabeled as `success` | **24/70** | 30/70 |
| Failures assigned the exact type | **19/70** | 8/70 |

Fixed 256 nearly doubles observed cost. Adaptive 256 costs 68.6% more than
fixed 128, while also decreasing all three accuracy measures.

**Decision: use 128 frames/view.**

## Additional note: temperature 0 is not deterministic

For the 30 long clips, fixed and adaptive 256 generated **23,040/23,040
byte-identical input-image pairs**, but the resulting predictions agreed on
only:

| Prompt | Identical predictions |
|---|---:|
| P1 | 26/30 |
| P2 primary type | 15/30 |
| P3/P5 primary type | 24/30 |

Temperature 0 does not make Gemini 3.1 Pro deterministic through OpenRouter.

## Notes

- P1 is binary success/failure accuracy.
- P2 and parsed P3/P5 require an exact primary-type match among success and seven
  failure types.
- Evaluations use **front + left + right**. `front_lower` is stored for dataset
  compatibility but is not sent to the VLM.
- Costs include all three prompts, the P5 parser, and retries with reported usage.
