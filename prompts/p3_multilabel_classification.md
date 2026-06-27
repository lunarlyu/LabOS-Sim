You are evaluating a lab automation video.

Question: Identify ALL outcomes and errors in this video. First decide whether the task was performed correctly. If not, report EVERY failure subtype you observe — not just one.

Use the correct vortexing protocol as the reference: pick up a capped, non-empty
tube; place it on the vortexer; visibly vortex/agitate the liquid; remove the
tube; and place it into a suitable tube rack or holder that can hold it upright.

Allowed failure subtypes:

- `cap_open` — the tube's cap is off, missing, or not secured during handling or
  vortexing.
- `tube_drop` — a tube is dropped, falls, tips over, or is released outside a
  rack / vortexer / gripper.
- `tube_empty` — the vortexed tube has no visible liquid or sample in it.
- `vortex_off` — the vortexer does not run; no visible agitation while the tube
  is on it.
- `wrong_orientation` — the tube is placed or held in an incorrect orientation
  (e.g. upside-down, horizontal) when it should be upright.
- `wrong_rack` — the tube is placed into a rack or holder that cannot properly
  hold it (wrong size or type).
- `rack_flipped` — the destination rack or holder is upside-down, inverted, or
  on its side.
- `repeated_steps` — a protocol step is performed more than once unnecessarily.
- `other_failure` — a real deviation from correct execution that none of the
  subtypes above describe.

Instructions:

- Set `outcome` to `success` ONLY if the full protocol was completed with no deviation. Otherwise set it to `failure`.
- Evaluate each failure subtype independently: include a subtype in
  `failure_modes` if and only if you observe it, regardless of whether other
  subtypes are also present. Multiple subtypes can and should co-occur when more than one thing went wrong.
- `failure_modes` must be empty if and only if `outcome` is `success`.
- Order `failure_modes` by importance: list the single most important / most severe issue to fix FIRST.

Return exactly one JSON object:

{
  "outcome": "success",
  "failure_modes": [],
  "confidence": 0.0,
  "reasoning": "Brief visual evidence for each call."
}
