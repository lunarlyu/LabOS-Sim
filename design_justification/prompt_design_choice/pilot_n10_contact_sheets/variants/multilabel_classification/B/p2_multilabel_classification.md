You are evaluating a lab automation video.

Question: Identify ALL errors in this video. First decide whether the task was performed correctly. If not, report EVERY failure subtype you
observe — there might be one or multiple.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Allowed failure subtypes:

- `cap_open` — the target tube's cap is off, missing, or not secured during handling or vortexing.
- `tube_drop` — the target tube is dropped, falls, tips over, or is released outside a rack / vortexer / gripper.
- `tube_empty` — the target tube (the one being vortexed) has no visible liquid or sample in it.
- `vortex_off` — the vortexer does not run; no visible agitation, spinning, or movement of the contents while the target tube is on it.
- `wrong_orientation` — the target tube is placed or held in an incorrect orientation (e.g. upside-down, horizontal) when it should be upright.
- `wrong_rack` — the target tube is placed into a rack or holder that cannot properly hold it (wrong size or type).
- `rack_flipped` — the destination rack or holder where the target tube is placed is upside-down, inverted, or on its side.
- `other_failure` — a real deviation from the correct execution of the target tube's vortexing that none of the subtypes above describe.

Instructions:

- Set `outcome` to `success` ONLY if the full protocol was completed for the
  target tube with no deviation. Otherwise set it to `failure`.
- Evaluate each failure subtype independently: include a subtype in
  `failure_modes` if and only if you observe it, regardless of whether other
  subtypes are also present. Multiple subtypes can and should co-occur when more
  than one thing went wrong.
- `failure_modes` must be empty if and only if `outcome` is `success`.
- Order `failure_modes` by importance: list the single most important / most
  severe issue to fix FIRST.
- Use `other_failure` only for a real deviation that none of the named subtypes describe. When you include `other_failure` in `failure_modes`, describe each
  such novel deviation in `additional_failures` (with visual evidence).
  `additional_failures` must be non-empty if and only if `other_failure` is in `failure_modes`; if `other_failure` is not in `failure_modes`, leave
  `additional_failures` empty (`[]`).

Return exactly one JSON object with these fields. Replace every value below with
your own — do not copy the placeholder text:

{
  "outcome": "success" or "failure",
  "failure_modes": [<zero or more subtypes from the list above, most important first; empty iff success>],
  "confidence": <number 0.0-1.0: your certainty in the outcome, not a fixed value>,
  "reasoning": "<one or two sentences citing the specific visual evidence for each failure mode you list>",
  "additional_failures": [<one { "description": "...", "evidence": "..." } per other_failure; empty [] otherwise>]
}
