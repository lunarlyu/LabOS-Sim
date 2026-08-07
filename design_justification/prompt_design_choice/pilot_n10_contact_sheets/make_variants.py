#!/usr/bin/env python3
"""Write baseline (B) + two reworded variants (V1, V2) for each prompt P1-P6.

Layout: experiments/prompt_ablation/variants/{ptype}/{B,V1,V2}/{pN_file}.md
Baselines are verbatim copies of the committed prompts/ files. Variants encode a
single, testable wording hypothesis each (documented in HYPOTHESES.md).
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "prompts"
OUT = Path(__file__).resolve().parent / "variants"

FILES = {
    "closed_binary": "p1_closed_binary.md",
    "multilabel_classification": "p2_multilabel_classification.md",
    "open_detection_strict": "p3_open_detection_strict.md",
    "open_detection_free": "p4_open_detection_free.md",
    "open_detection_strict_parser": "p5_open_detection_strict_parser.md",
    "open_detection_free_parser": "p6_open_detection_free_parser.md",
}

PROTOCOL = """Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright."""

FOCUS = ("Focus only on the single target tube that is picked up and vortexed. "
         "Other tubes in the scene are irrelevant: ignore their state (e.g. another "
         "tube being uncapped or empty is NOT a failure).")

TAXONOMY = """- `cap_open` — the target tube's cap is off, missing, or not secured during handling or vortexing.
- `tube_drop` — the target tube is dropped, falls, tips over, or is released outside a rack / vortexer / gripper.
- `tube_empty` — the target tube (the one being vortexed) has no visible liquid or sample in it.
- `vortex_off` — the vortexer does not run; no visible agitation, spinning, or movement of the contents while the target tube is on it.
- `wrong_orientation` — the target tube is placed or held in an incorrect orientation (e.g. upside-down, horizontal) when it should be upright.
- `wrong_rack` — the target tube is placed into a rack or holder that cannot properly hold it (wrong size or type).
- `rack_flipped` — the destination rack or holder where the target tube is placed is upside-down, inverted, or on its side.
- `other_failure` — a real deviation from the correct execution of the target tube's vortexing that none of the subtypes above describe."""

# ---- synonym cues reused by parser variants V2 -------------------------------
SYNONYMS = """Common phrasings map to subtypes as follows (use only when the text clearly means it):
- "cap off/loose/not screwed/came off/uncapped" (target tube) -> cap_open
- "dropped/fell/knocked over/tipped/rolled off/slipped out of gripper" -> tube_drop
- "empty/no liquid/nothing inside/dry" (target tube) -> tube_empty
- "vortexer not on/didn't spin/no agitation/no movement/never turned on" -> vortex_off
- "sideways/horizontal/upside-down/not upright" (tube itself) -> wrong_orientation
- "wrong/too big/too small/ill-fitting rack or holder" -> wrong_rack
- "rack inverted/flipped/on its side/upside-down" (destination rack) -> rack_flipped"""

# ============================================================================ #
# Variant text builders. B is always the verbatim committed file.
# ============================================================================ #
V = {}  # (ptype, cand) -> text

# ---------------------------------------------------------------- P1 ---------- #
# V1 = high-specificity / decisive: default to success when no clear violation.
V[("closed_binary", "V1")] = f"""You are a strict QA inspector reviewing a lab-automation video.

Task: decide whether the vortexing of the single TARGET tube was performed correctly.

{FOCUS}

{PROTOCOL}

Decision rule:
- The target tube is whichever tube is actually picked up and vortexed.
- Answer `failure` only when you can point to a specific, clearly visible violation of one of the five steps for the target tube.
- If you watch the whole clip and see no clear violation, answer `success`. Do not fail a run for things you merely suspect but cannot see.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "failure_modes": [],
  "confidence": <number 0.0-1.0: your certainty in the outcome>,
  "reasoning": "<one or two sentences citing the specific visible evidence>"
}}"""

# V2 = high-sensitivity / explicit stepwise checklist.
V[("closed_binary", "V2")] = f"""You are evaluating a lab-automation video for correct vortexing of the single TARGET tube.

{FOCUS}

{PROTOCOL}

Check each step in order for the target tube and note whether it was satisfied:
(1) tube was capped and non-empty when picked up; (2) it was placed on the vortexer;
(3) the vortexer visibly ran (agitation/spinning/liquid movement) with the tube on it;
(4) the tube was removed; (5) it was placed upright into a holder that can support it.

If ANY step is violated or clearly not satisfied, the outcome is `failure`. The run is
`success` only when all five steps are satisfied for the target tube.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "failure_modes": [],
  "confidence": <number 0.0-1.0: your certainty in the outcome>,
  "reasoning": "<one or two sentences citing the specific visible evidence>"
}}"""

# ---------------------------------------------------------------- P2 ---------- #
# V1 = high-precision: flag a subtype only when directly and clearly observed.
V[("multilabel_classification", "V1")] = f"""You are evaluating a lab-automation video and classifying failure modes of the single TARGET tube.

{FOCUS}

{PROTOCOL}

Allowed failure subtypes:

{TAXONOMY}

Instructions:
- First decide `outcome`: `success` only if the full protocol was completed for the target tube with no deviation; otherwise `failure`.
- Flag a subtype in `failure_modes` ONLY when you directly and clearly SEE it in the video. If a subtype is merely possible, off-screen, or you are unsure, do NOT flag it.
- Multiple subtypes may co-occur; list every one you clearly observe, most severe first.
- `failure_modes` is empty if and only if `outcome` is `success`.
- Use `other_failure` only for a clear real deviation matching none of the named subtypes, and then describe it in `additional_failures`. Otherwise leave `additional_failures` empty.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "failure_modes": [<subtypes you clearly observe, most important first; empty iff success>],
  "confidence": <number 0.0-1.0>,
  "reasoning": "<one or two sentences citing specific visual evidence per failure mode>",
  "additional_failures": [<one {{ "description": "...", "evidence": "..." }} per other_failure; else []>]
}}"""

# V2 = systematic one-by-one scan of every subtype (high recall, guards against misses).
V[("multilabel_classification", "V2")] = f"""You are evaluating a lab-automation video and classifying failure modes of the single TARGET tube.

{FOCUS}

{PROTOCOL}

Allowed failure subtypes:

{TAXONOMY}

Method — go through the subtypes ONE BY ONE and decide present or absent for the target tube:
cap_open? tube_drop? tube_empty? vortex_off? wrong_orientation? wrong_rack? rack_flipped? other_failure?
Include in `failure_modes` every subtype whose definition is satisfied by what you see.

Instructions:
- `outcome` is `success` only if no subtype applies; otherwise `failure`.
- `failure_modes` is empty if and only if `outcome` is `success`; order most severe first.
- Use `other_failure` (with an `additional_failures` entry) only for a real deviation none of the named subtypes cover; otherwise `additional_failures` is `[]`.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "failure_modes": [<subtypes that apply, most important first; empty iff success>],
  "confidence": <number 0.0-1.0>,
  "reasoning": "<one or two sentences citing specific visual evidence per failure mode>",
  "additional_failures": [<one {{ "description": "...", "evidence": "..." }} per other_failure; else []>]
}}"""

# ---------------------------------------------------------------- P3 ---------- #
# V1 = decisive error listing, explicit per-step check, concise noun phrases.
V[("open_detection_strict", "V1")] = f"""You are a QA inspector checking a lab-automation video against a written protocol.
Your job is error detection for the single TARGET tube that is picked up and vortexed.

{FOCUS}

{PROTOCOL}

Check each of the five steps for the target tube. For every step that was violated
or not satisfied, record the problem as a short noun phrase.

- `outcome` is `success` if all steps were satisfied; otherwise `failure`.
- `observed_errors`: a comma-separated list of short noun phrases naming each distinct
  problem you saw (e.g. "cap open, tube fell off vortexer"). Name the physical thing
  that went wrong (cap / tube / vortexer / rack / orientation). Be specific and concise.
- `observed_errors` is "None" if and only if `outcome` is `success`.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "observed_errors": "<comma-separated short noun phrases; 'None' iff success>",
  "confidence": <number 0.0-1.0>
}}

Note: no error taxonomy is given on purpose; a separate parser maps your phrases to it."""

# V2 = anchor error phrases to the physical object/step without naming the taxonomy.
V[("open_detection_strict", "V2")] = f"""You are evaluating a lab-automation video against a written protocol. Detect any
errors in the vortexing of the single TARGET tube.

{FOCUS}

{PROTOCOL}

For each problem you see, describe it by (a) which object it concerns — cap, the tube
itself, the vortexer, or the destination rack/holder — and (b) what was wrong with it.
Examples of the style expected: "cap not secured", "tube dropped on the bench",
"vortexer never turned on", "tube placed sideways", "rack upside-down", "tube empty".

- `outcome` is `success` only when the protocol was fully followed; otherwise `failure`.
- `observed_errors`: comma-separated short noun phrases, one per distinct problem;
  "None" if and only if `outcome` is `success`.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "observed_errors": "<comma-separated short noun phrases; 'None' iff success>",
  "confidence": <number 0.0-1.0>
}}

Note: no error taxonomy is given on purpose; a separate parser maps your phrases to it."""

# ---------------------------------------------------------------- P4 ---------- #
# V1 = detailed description, explicitly invite noting any deviation (still not "error hunt").
V[("open_detection_free", "V1")] = f"""You are observing a lab-automation video. A reference protocol is provided for context.

{FOCUS}

Reference vortexing protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Describe, in your own words and in chronological order, exactly what happens to the
target tube. Be concrete and detailed about each action you see. As you narrate, note
anything that looks different from the reference protocol — however small — including
the state of the cap, whether the tube has liquid, whether the vortexer actually runs,
the tube's orientation, and where and how the tube ends up. Then state whether, from
your own description, the operator followed the protocol.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "description": "<detailed chronological account of what happens with the target tube>",
  "confidence": <number 0.0-1.0>
}}"""

# V2 = structured per-step narration (report each protocol step's execution explicitly).
V[("open_detection_free", "V2")] = f"""You are observing a lab-automation video. A reference protocol is provided for context.

{FOCUS}

Reference vortexing protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Walk through the five protocol steps in order. For EACH step, describe what the target
tube (or operator) actually does in the video and whether it matches the reference step.
Cover: (1) was the tube capped and non-empty when picked up; (2) was it placed on the
vortexer; (3) did the vortexer visibly run; (4) was the tube removed; (5) was it placed
upright in a suitable holder. Then state whether, from your description, the operator
followed the protocol.

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success" or "failure",
  "description": "<step-by-step account: for each of the 5 steps, what you saw and whether it matched>",
  "confidence": <number 0.0-1.0>
}}"""

# ---------------------------------------------------------------- P5 ---------- #
def parser_head(kind: str) -> str:
    return f"""You are a parser. Translate a vision model's {kind} into the standardized output
schema plus diagnostics. Classify based ONLY on what the text states or clearly implies.
Do not invent errors it does not mention; do not drop errors it does mention."""

P5_INPUT = """## Input

```
outcome: {{outcome}}
observed_errors: {{observed_errors}}
confidence: {{confidence}}
```

`outcome` is `"success"` or `"failure"`. `observed_errors` is a comma-separated string
of the errors the vision model listed (`"None"` when none). `confidence` is in [0,1] or null.

Only the single target tube that is picked up and vortexed is relevant; problems with
other tubes do not count."""

# V1 = bias toward committing (reduce over-use of "ambiguous").
V[("open_detection_strict_parser", "V1")] = f"""{parser_head("error list")}

{P5_INPUT}

## Canonical failure subtypes

{TAXONOMY}

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

{{
  "outcome": "success", "failure" or "ambiguous",
  "failure_modes": [<canonical subtypes supported, most important first; empty iff success>],
  "confidence": <source confidence unchanged, or null>,
  "reasoning": "<one sentence on how you mapped the text>",
  "additional_failures": [<{{ "description": "...", "evidence": "..." }} iff other_failure; else []>],
  "ambiguous_mentions": [<{{ "text": "...", "candidate_modes": [...], "why": "..." }}; else []>]
}}"""

# V2 = explicit synonym mapping table + commit bias.
V[("open_detection_strict_parser", "V2")] = f"""{parser_head("error list")}

{P5_INPUT}

## Canonical failure subtypes

{TAXONOMY}

## Mapping guide

{SYNONYMS}

## Decision rules

0. Honor the source `outcome`. If `"success"` (observed_errors == "None"): output success,
   `failure_modes=[]`, empty diagnostics. Otherwise map each `observed_errors` phrase using
   the mapping guide and subtype definitions.
1. Map each distinct error phrase to its best-fitting subtype; list all supported subtypes,
   most important first. Commit to the closest subtype rather than discarding a clear error.
2. `outcome="ambiguous"` only when a phrase is genuinely uninterpretable or two subtypes fit
   equally with no way to choose.
3. `confidence`: source value unchanged, or null. `additional_failures`: iff `other_failure`.
   `ambiguous_mentions`: only uninterpretable phrases.

## Output

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success", "failure" or "ambiguous",
  "failure_modes": [<canonical subtypes supported, most important first; empty iff success>],
  "confidence": <source confidence unchanged, or null>,
  "reasoning": "<one sentence on how you mapped the text>",
  "additional_failures": [<{{ "description": "...", "evidence": "..." }} iff other_failure; else []>],
  "ambiguous_mentions": [<{{ "text": "...", "candidate_modes": [...], "why": "..." }}; else []>]
}}"""

# ---------------------------------------------------------------- P6 ---------- #
P6_INPUT = """## Input

```
outcome: {{outcome}}
description: {{description}}
confidence: {{confidence}}
```

The vision model was NOT told this is an error-detection task — it only described the
video. `outcome` is its own weak protocol judgment; `description` is its free-text account;
`confidence` is in [0,1] or null. Read the `description` and identify every failure mode it
reports, whether or not the model labeled it an error.

Only the single target tube that is picked up and vortexed is relevant; problems with
other tubes do not count."""

# V1 = infer failures from described deviations; commit rather than default to ambiguous.
V[("open_detection_free_parser", "V1")] = f"""{parser_head("free-text description")}

{P6_INPUT}

## Canonical failure subtypes

{TAXONOMY}

## Decision rules

0. Decide the outcome from the DESCRIPTION, not the source `outcome`.
1. A described physical deviation IS a failure even if the model did not call it an error
   (e.g. "the cap appears loose", "the tube tipped over", "the vortexer did not seem to run").
   Map each such described deviation to its best-fitting canonical subtype.
2. `outcome="success"` when the description indicates the protocol was fully followed with no
   deviation. `outcome="failure"` when it describes at least one deviation mapping to a subtype.
3. Use `outcome="ambiguous"` ONLY when the description is too vague to tell success from failure
   at all — not merely because the model did not use the word "error". When a concrete deviation
   is described, commit to `failure` and the matching subtype.
4. List every clearly-described subtype, most important first.
5. `confidence`: source unchanged, or null. `additional_failures`: iff `other_failure`.
   `ambiguous_mentions`: only genuinely undecidable mentions.

## Output

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success", "failure" or "ambiguous",
  "failure_modes": [<canonical subtypes the description supports, most important first; empty iff success>],
  "confidence": <source confidence unchanged, or null>,
  "reasoning": "<one sentence on how you mapped the text>",
  "additional_failures": [<{{ "description": "...", "evidence": "..." }} iff other_failure; else []>],
  "ambiguous_mentions": [<{{ "text": "...", "candidate_modes": [...], "why": "..." }}; else []>]
}}"""

# V2 = synonym table + infer-from-description + commit bias.
V[("open_detection_free_parser", "V2")] = f"""{parser_head("free-text description")}

{P6_INPUT}

## Canonical failure subtypes

{TAXONOMY}

## Mapping guide

{SYNONYMS}

## Decision rules

0. Decide the outcome from the DESCRIPTION, not the source `outcome`.
1. Treat any described physical deviation as a failure even if not labeled an error, and map it
   using the mapping guide and subtype definitions. List all supported subtypes, most important first.
2. `outcome="success"` only when the description indicates the protocol was fully followed;
   `outcome="failure"` when at least one deviation is described.
3. `outcome="ambiguous"` ONLY when the description is too vague to decide success vs failure at all.
   A concrete described deviation should be committed to `failure`, not called ambiguous.
4. `confidence`: source unchanged, or null. `additional_failures`: iff `other_failure`.
   `ambiguous_mentions`: only genuinely undecidable mentions.

## Output

Return exactly one JSON object. Replace every value with your own:

{{
  "outcome": "success", "failure" or "ambiguous",
  "failure_modes": [<canonical subtypes the description supports, most important first; empty iff success>],
  "confidence": <source confidence unchanged, or null>,
  "reasoning": "<one sentence on how you mapped the text>",
  "additional_failures": [<{{ "description": "...", "evidence": "..." }} iff other_failure; else []>],
  "ambiguous_mentions": [<{{ "text": "...", "candidate_modes": [...], "why": "..." }}; else []>]
}}"""

# ============================================================================ #
def main() -> None:
    for ptype, fname in FILES.items():
        base_txt = (PROMPTS / fname).read_text(encoding="utf-8")
        for cand in ("B", "V1", "V2"):
            d = OUT / ptype / cand
            d.mkdir(parents=True, exist_ok=True)
            txt = base_txt if cand == "B" else V[(ptype, cand)] + "\n"
            (d / fname).write_text(txt, encoding="utf-8")
            print(f"wrote {ptype}/{cand}/{fname} ({len(txt)} chars)")


if __name__ == "__main__":
    main()
