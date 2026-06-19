You are evaluating a lab automation video.

Question: Which single outcome or error subtype best describes this video?

Allowed choices:

- success
- cap_open
- tube_drop
- tube_empty
- vortex_off
- wrong_orientation
- wrong_rack
- rack_flipped
- repeated_steps
- other_failure

Choose `success` only if the operator completed the full vortexing protocol:
pick up a capped, non-empty tube; place it on the vortexer; visibly agitate the
liquid; remove the tube; and place it into a suitable rack or holder.

Return exactly one JSON object:

{
  "choice": "success",
  "outcome": "success",
  "primary_failure_mode": null,
  "failure_modes": [],
  "confidence": 0.0,
  "reasoning": "Brief visual evidence."
}
