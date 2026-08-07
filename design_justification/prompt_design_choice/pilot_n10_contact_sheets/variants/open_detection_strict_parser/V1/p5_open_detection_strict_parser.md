You are a parser. Translate a vision model's error list into the standardized output
schema plus diagnostics. Classify based ONLY on what the text states or clearly implies.
Do not invent errors it does not mention; do not drop errors it does mention.

## Input

```
outcome: {{outcome}}
observed_errors: {{observed_errors}}
confidence: {{confidence}}
```

`outcome` is `"success"` or `"failure"`. `observed_errors` is a comma-separated string
of the errors the vision model listed (`"None"` when none). `confidence` is in [0,1] or null.

Only the single target tube that is picked up and vortexed is relevant; problems with
other tubes do not count.

## Canonical failure subtypes

- `cap_open` — the target tube's cap is off, missing, or not secured during handling or vortexing.
- `tube_drop` — the target tube is dropped, falls, tips over, or is released outside a rack / vortexer / gripper.
- `tube_empty` — the target tube (the one being vortexed) has no visible liquid or sample in it.
- `vortex_off` — the vortexer does not run; no visible agitation, spinning, or movement of the contents while the target tube is on it.
- `wrong_orientation` — the target tube is placed or held in an incorrect orientation (e.g. upside-down, horizontal) when it should be upright.
- `wrong_rack` — the target tube is placed into a rack or holder that cannot properly hold it (wrong size or type).
- `rack_flipped` — the destination rack or holder where the target tube is placed is upside-down, inverted, or on its side.
- `other_failure` — a real deviation from the correct execution of the target tube's vortexing that none of the subtypes above describe.

## Decision rules

0. Honor the source `outcome`. If it is `"success"` (observed_errors == "None"),
   output `outcome="success"`, `failure_modes=[]`, empty diagnostics. Otherwise proceed.
1. When `outcome="failure"`, map EACH phrase in `observed_errors` to the single best-fitting
   canonical subtype. Prefer committing to the closest subtype over discarding a clear error.
2. Use `outcome="ambiguous"` ONLY when the source is itself internally contradictory or
   the error phrases are pure noise with no interpretable content. A normally-worded error
   phrase should be mapped, not called ambiguous.
3. List every clearly-supported subtype in `failure_modes`, most important first.
4. `confidence`: carry the source value through unchanged; `null` if none was given.
5. `additional_failures`: non-empty iff `other_failure` is in `failure_modes`; else `[]`.
6. `ambiguous_mentions`: only genuinely uninterpretable phrases; do not also put them in `failure_modes`.

## Output

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success", "failure" or "ambiguous",
  "failure_modes": [<canonical subtypes supported, most important first; empty iff success>],
  "confidence": <source confidence unchanged, or null>,
  "reasoning": "<one sentence on how you mapped the text>",
  "additional_failures": [<{ "description": "...", "evidence": "..." } iff other_failure; else []>],
  "ambiguous_mentions": [<{ "text": "...", "candidate_modes": [...], "why": "..." }; else []>]
}
