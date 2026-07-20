# Appendix A. VLM Input Design Selection

## A.1. Study objective and selected configuration

We conducted a development-set study to select the VLM input configuration used
in the main experiments. The selected configuration uses **independent frames,
128 frames per view, front + left + right views, a maximum frame width of 720
px, and 2,048 maximum output tokens**.

The study used one VLM (Gemini 3.1 Pro) and 80 human-executed vortexing clips:
10 successful executions and 10 examples from each of seven primary failure
types. These clips are treated as development data and are excluded from any
held-out performance claim.

## A.2. Evaluation protocol

All conditions use the same sample IDs. We evaluate three prompting paths:

- **P1:** binary success/failure classification;
- **P2:** structured classification, scored by the first returned primary type;
- **P3/P5:** open-ended detection followed by a fixed parser.

P2 and P3/P5 require an exact match among eight mutually exclusive labels:
`success`, `cap_open`, `tube_drop`, `tube_empty`, `vortex_off`,
`wrong_orientation`, `wrong_rack`, and `rack_flipped`. If P2 returns multiple
types, only the first is scored. P1 is reported using accuracy and balanced
accuracy, where balanced accuracy is the mean of success recall and failure
recall. The latter is important because the set contains 10 successes and 70
failures.

Calls use temperature 0 and retry after failure. Unless ablated, the maximum
output length is 2,048 tokens. Reported cost includes P1, P2, P3, parser calls,
and retries for which usage was reported.

The study was conducted in two stages. Contact-sheet experiments used front and
gripper views, whereas independent-frame experiments used front, left, and right
views with explicit view markers. Consequently, the cross-representation
comparison is informative but not a fully controlled causal ablation. Camera
selection itself was based on coverage inspection and was not evaluated as a
view-count ablation.

## A.3. Contact sheets versus independent frames

| Frames/view | Representation | P1 accuracy | P2 exact | P3/P5 exact | Cost |
|---:|---|---:|---:|---:|---:|
| 128 | Contact sheet | 42/80 (52.5%) | 11/80 (13.8%) | 13/80 (16.3%) | $4.88 |
| 128 | Independent frames | 22/80 (27.5%) | **24/80 (30.0%)** | **15/80 (18.8%)** | $409.44 |
| 256 | Contact sheet | 40/80 (50.0%) | 14/80 (17.5%) | 7/80 (8.8%) | $4.72 |
| 256 | Independent frames | 19/80 (23.8%) | **15/80 (18.8%)** | **14/80 (17.5%)** | $770.29 |

Independent frames improve exact-type accuracy at both frame counts, although
P1 accuracy is lower. At 256 frames, a single contact sheet contains a 16 x 16
grid. Provider-side resizing or compression may reduce the effective resolution
of each tile; this is a plausible explanation for the lack of benefit from the
larger sheet, but the provider's internal preprocessing is not observable.

We use independent frames because the primary objective is fine-grained failure
identification rather than binary classification. This choice increases cost
substantially and should not be interpreted as an efficiency improvement.

## A.4. Resolution

This comparison uses 128 independent frames per view.

| Maximum width | P1 accuracy | P1 balanced | P2 exact | P3/P5 exact | Cost |
|---:|---:|---:|---:|---:|---:|
| 720 px | 22/80 (27.5%) | **50.0%** | **24/80 (30.0%)** | **15/80 (18.8%)** | **$409.44** |
| 480 px | **24/80 (30.0%)** | 47.1% | 16/80 (20.0%) | 9/80 (11.3%) | $413.51 |

The two-point increase in raw P1 accuracy at 480 px does not indicate a general
improvement: balanced accuracy decreases, as do both exact-type metrics. Raw
inspection shows that the lower-resolution condition predicts `tube_empty`
more often, including for examples with other primary labels. This response
bias contributes to the apparent P1 gain. We therefore retain 720 px.

## A.5. Output-token limit

This ablation uses 128-frame contact sheets.

| Output-token limit | P1 accuracy | P1 balanced | P2 exact | P3/P5 exact | Cost |
|---:|---:|---:|---:|---:|---:|
| 2,048 | **42/80 (52.5%)** | 55.7% | **11/80 (13.8%)** | **13/80 (16.3%)** | $4.88 |
| 4,096 | 39/80 (48.8%) | **57.9%** | 10/80 (12.5%) | 11/80 (13.8%) | **$4.75** |

Of 720 retained 2,048-token VLM outputs in the contact-sheet experiments, 718
ended with `finish_reason=stop`; only two ended because of the length limit.
Increasing the limit therefore addresses almost no observed truncation and
provides no consistent accuracy benefit. We retain 2,048 output tokens. The
small cost difference is attributable to realized output and retry behavior,
not to a lower price for the larger limit.

## A.6. Number of independent frames

Fixed 256 always emits 256 frames per view and duplicates frames when a source
stream is shorter. Adaptive 256 emits all decoded frames below 256 and uniformly
samples 256 otherwise.

| Setting | P1 accuracy | P1 balanced | P2 exact | P3/P5 exact | Completed cost |
|---|---:|---:|---:|---:|---:|
| Fixed 128 | **22/80 (27.5%)** | **50.0%** | **24/80 (30.0%)** | **15/80 (18.8%)** | **$409.44** |
| Fixed 256 | 19/80 (23.8%) | 47.9% | 15/80 (18.8%) | 14/80 (17.5%) | $770.29 |
| Adaptive 256 | 18/80 (22.5%) | 47.1% | 17/80 (21.3%) | 11/80 (13.8%) | $690.29 |

Adaptive 256 costs 68.6% more than fixed 128 while decreasing P1, P2 exact, and
P3/P5 exact accuracy. Avoiding duplicated frames therefore does not recover the
fixed-256 performance gap.

### A.6.1. Fixed 256 and duplicated frames

Source length is the decoded frame count, not duration multiplied by nominal
frame rate. Across the 240 selected camera streams, counts range from 89 to 463
(median 246); 150/240 streams are shorter than 256 frames. At the clip level,
50/80 examples have at least one selected view below 256 frames.

| Minimum source length | n | Prompt | Fixed 128 | Fixed 256 |
|---|---:|---|---:|---:|
| <256 | 50 | P1 | **15/50 (30.0%)** | 9/50 (18.0%) |
|  |  | P2 exact | **16/50 (32.0%)** | 9/50 (18.0%) |
|  |  | P3/P5 exact | **9/50 (18.0%)** | 7/50 (14.0%) |
| >=256 | 30 | P1 | 7/30 (23.3%) | **10/30 (33.3%)** |
|  |  | P2 exact | **8/30 (26.7%)** | 6/30 (20.0%) |
|  |  | P3/P5 exact | 6/30 (20.0%) | **7/30 (23.3%)** |

The fixed-256 decrease is concentrated among shorter clips, for which the
pipeline repeats frames. For clips with at least 256 genuine frames, P1 and
P3/P5 improve modestly, while P2 still decreases. More frames therefore do not
produce a task-consistent benefit even when duplication is absent.

### A.6.2. Adaptive 256 by source length

| Minimum source length | n | Prompt | Fixed 128 | Adaptive 256 |
|---|---:|---|---:|---:|
| <128 | 4 | P1 | 1/4 (25.0%) | **3/4 (75.0%)** |
|  |  | P2 exact | 0/4 (0.0%) | 0/4 (0.0%) |
|  |  | P3/P5 exact | 0/4 (0.0%) | 0/4 (0.0%) |
| 128--255 | 46 | P1 | **14/46 (30.4%)** | 7/46 (15.2%) |
|  |  | P2 exact | **16/46 (34.8%)** | 8/46 (17.4%) |
|  |  | P3/P5 exact | **9/46 (19.6%)** | 5/46 (10.9%) |
| >=256 | 30 | P1 | 7/30 (23.3%) | **8/30 (26.7%)** |
|  |  | P2 exact | 8/30 (26.7%) | **9/30 (30.0%)** |
|  |  | P3/P5 exact | 6/30 (20.0%) | 6/30 (20.0%) |

The adaptive decrease is concentrated in the 46 clips with 128--255 source
frames, where all three prompting paths decrease. Possible mechanisms include
dilution of brief failure cues by many similar adjacent frames and increased
distance between corresponding temporal regions in the three view groups. For
the 30 clips with at least 256 source frames, P1 and P2 each improve by one
correct prediction, while P3/P5 is unchanged. These explanations are post-hoc
hypotheses, not controlled causal findings.

### A.6.3. P2 success bias

| P2 behavior | Fixed 128 | Adaptive 256 |
|---|---:|---:|
| Predicted `success` | 29/80 | 39/80 |
| True successes predicted correctly | 5/10 | **9/10** |
| Failures predicted as `success` | **24/70** | 30/70 |
| Failures assigned the exact type | **19/70** | 8/70 |

Adaptive 256 adds 10 success predictions. Four recover true successes, but six
are new false-success predictions, and exact failure-type accuracy decreases
substantially. This shift explains part of the aggregate P2 decrease.

### A.6.4. Identical-input replication check

For the 30 clips whose three views each contain at least 256 frames, fixed and
adaptive 256 apply the same transformation. All 23,040 corresponding JPEG pairs
(30 clips x 3 views x 256 frames) are byte-identical.

| Prompt | Fixed 256 accuracy | Adaptive 256 accuracy | Identical predictions |
|---|---:|---:|---:|
| P1 | 10/30 (33.3%) | 8/30 (26.7%) | 26/30 (86.7%) |
| P2 exact | 6/30 (20.0%) | 9/30 (30.0%) | 15/30 (50.0%) |
| P3/P5 exact | 7/30 (23.3%) | 6/30 (20.0%) | 24/30 (80.0%) |

Despite identical inputs and inference settings, predictions differ across
runs. Temperature 0 therefore does not make separate provider calls fully
deterministic. Small single-run differences cannot be attributed confidently to
the frame-selection policy.

## A.7. Paired analysis

We compare each independent-frame alternative with fixed 128 using paired
correctness flips. No unadjusted two-sided exact McNemar test is significant at
0.05.

| Alternative | Prompt | Wrong-to-correct | Correct-to-wrong | Exact p-value |
|---|---|---:|---:|---:|
| Fixed 256 | P1 | 7 | 10 | 0.629 |
| Fixed 256 | P2 exact | 5 | 14 | 0.064 |
| Fixed 256 | P3/P5 exact | 3 | 4 | 1.000 |
| Adaptive 256 | P1 | 5 | 9 | 0.424 |
| Adaptive 256 | P2 exact | 8 | 15 | 0.210 |
| Adaptive 256 | P3/P5 exact | 3 | 7 | 0.344 |
| 480 px | P1 | 11 | 9 | 0.824 |
| 480 px | P2 exact | 8 | 16 | 0.152 |
| 480 px | P3/P5 exact | 1 | 7 | 0.070 |

These tests are descriptive, post hoc, and not corrected for multiple
comparisons. They support a conservative selection: none of the higher-cost or
lower-resolution alternatives demonstrates a reliable improvement.

## A.8. Final design choice and limitations

We use **128 independent frames per view at 720 px with a 2,048-token output
limit**. This setting has the strongest completed P2 exact-type accuracy among
the independent-frame conditions, avoids the near-doubling in cost observed for
fixed 256, and does not rely on the class-response shift observed at 480 px.
Front, left, and right views are fixed from coverage inspection and are not
claimed as the outcome of a camera ablation.

The study has four main limitations. First, each condition is evaluated once
per clip, and the identical-input check reveals substantial run-to-run
variation. Second, the source-length and response-bias analyses are post hoc.
Third, P3/P5 evaluates a VLM-plus-parser pipeline rather than the VLM alone.
Fourth, the contact-sheet and independent-frame stages differ in camera views
and input markers. Accordingly, this study supports an engineering choice for
the subsequent evaluation; it does not establish a general causal advantage of
one input representation.

## A.9. Reproducibility details

The sample manifest was generated once with seed `20260711` and then held fixed
across conditions. Its SHA-256 digest is
`64cf39c8757787d42e7d882e9691e8caca528b2faacbb9d21d6a7324b8d35711`.
Independent frames are sampled uniformly over each decoded stream, ordered
chronologically within each view, resized with preserved aspect ratio, and
encoded as JPEG. The complete anonymous supplementary artifact contains the
manifest, condition configurations, raw predictions, usage ledgers, parsed
outputs, and metric tables.
