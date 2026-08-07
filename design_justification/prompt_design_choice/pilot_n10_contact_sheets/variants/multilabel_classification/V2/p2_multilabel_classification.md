You are evaluating a lab-automation video and classifying failure modes of the single TARGET tube.

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

Method — go through the subtypes ONE BY ONE and decide present or absent for the target tube:
cap_open? tube_drop? tube_empty? vortex_off? wrong_orientation? wrong_rack? rack_flipped? other_failure?
Include in `failure_modes` every subtype whose definition is satisfied by what you see.

Instructions:
- `outcome` is `success` only if no subtype applies; otherwise `failure`.
- `failure_modes` is empty if and only if `outcome` is `success`; order most severe first.
- Use `other_failure` (with an `additional_failures` entry) only for a real deviation none of the named subtypes cover; otherwise `additional_failures` is `[]`.

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success" or "failure",
  "failure_modes": [<subtypes that apply, most important first; empty iff success>],
  "confidence": <number 0.0-1.0>,
  "reasoning": "<one or two sentences citing specific visual evidence per failure mode>",
  "additional_failures": [<one { "description": "...", "evidence": "..." } per other_failure; else []>]
}
