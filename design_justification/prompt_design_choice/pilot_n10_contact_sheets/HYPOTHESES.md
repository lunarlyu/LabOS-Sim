# Prompt-ablation hypotheses

Each prompt P1–P6 is tested as **B** (verbatim current prompt) plus two reworded
variants, each encoding ONE testable wording hypothesis. Models: `qwen3_vl`,
`claude_opus_4_8`, `gemini_3_1_pro`. Data: 10 clips (3 success + 7 failures, one
per subtype). Parsers use `gpt_5_5_parser`.

| Prompt | V1 hypothesis | V2 hypothesis |
|---|---|---|
| P1 closed binary | High-specificity / decisive: "fail only on a clearly visible violation; otherwise success" → fewer false alarms | High-sensitivity: explicit 5-step checklist, fail if ANY step violated → higher failure recall |
| P2 multilabel | High-precision: flag a subtype only when directly and clearly seen | High-recall: scan every subtype one-by-one (guards against misses) |
| P3 strict | Decisive per-step error listing, name the physical object that went wrong | Anchor each error phrase to object+defect (cap/tube/vortexer/rack) for cleaner parser mapping |
| P4 free | Detailed description, invite noting any deviation (without calling it an error hunt) | Structured per-step narration: report each of the 5 steps' execution |
| P5 strict parser | Commit bias: map every error phrase to closest subtype; use `ambiguous` only for noise | + explicit synonym→subtype mapping guide |
| P6 free parser | Infer failures from described deviations even if unlabeled; commit over `ambiguous` | + explicit synonym→subtype mapping guide |

Scoring (per candidate, aggregated across the 3 models and per model):
- **P1/P3/P4** (binary outcome): balanced accuracy = mean(success recall, failure recall).
- **P2/P5/P6** (subtype): balanced accuracy + macro-F1 over subtypes; `ambiguous` rows
  count as scored (not held out) so a parser that dodges via `ambiguous` is penalized.

The winning candidate per prompt is the one with the highest mean balanced accuracy
across models (macro-F1 as tie-break), preferring **B** on ties (no change without gain).
