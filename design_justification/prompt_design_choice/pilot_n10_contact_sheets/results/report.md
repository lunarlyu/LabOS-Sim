# Prompt-ablation results (scored from raw predictions; `ambiguous` = miss)

Mean balanced accuracy across qwen3_vl / claude_opus_4_8 / gemini_3_1_pro,
10 clips (3 success + 7 single-mode failures). macro-F1 over 7 subtypes (P2-P6).


## P1 → winner: **V1**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B | 0.484 | nan | 0 |
| V1 ⭐ | 0.587 | nan | 0 |
| V2 | 0.508 | nan | 0 |

## P2 → winner: **V1**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B | 0.460 | 0.010 | 0 |
| V1 ⭐ | 0.524 | 0.067 | 0 |
| V2 | 0.500 | 0.022 | 0 |

## P3 → winner: **B**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B ⭐ | 0.587 | 0.011 | 0 |
| V1 | 0.532 | 0.024 | 0 |
| V2 | 0.532 | 0.033 | 0 |

## P4 → winner: **V2**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B | 0.357 | 0.000 | 9 |
| V1 | 0.460 | 0.032 | 5 |
| V2 ⭐ | 0.643 | 0.024 | 2 |

## P5 → winner: **V2**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B | 0.587 | 0.011 | 0 |
| V1 | 0.587 | 0.011 | 0 |
| V2 ⭐ | 0.587 | 0.034 | 0 |

## P6 → winner: **V2**
| cand | mean_balanced | mean_macro_f1 | ambig |
|---|---|---|---|
| B | 0.357 | 0.000 | 9 |
| V1 | 0.429 | 0.032 | 3 |
| V2 ⭐ | 0.476 | 0.016 | 1 |

## Winners
| prompt | winner |
|---|---|
| p1 | V1 |
| p2 | V1 |
| p3 | B |
| p4 | V2 |
| p5 | V2 |
| p6 | V2 |
