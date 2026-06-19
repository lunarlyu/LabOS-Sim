You are evaluating a lab automation video.

Task: choose the single most likely outcome for the vortexing scenario.

The allowed choices are:

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

A successful vortexing task has all of these properties:

- A tube is picked up.
- The tube is placed onto a vortexer.
- The vortexer runs: any visible movement/spinning/agitation of the liquid contents is enough to count as the vortexer working and on. The spin does not need to last for a minimum duration.
- The tube is taken off the vortexer.
- The tube is placed into a tube holder or test tube rack.
- The tube is non-empty.
- The vortexed tube can be any tube in the scene.
- The tube has a cap on it.
- The tube holder/rack can actually hold the tube, meaning the tube diameter is smaller than the holder diameter.

Choose `success` only if all success criteria are visibly satisfied.

If the task fails, choose exactly one failure mode: the most important visible failure that best explains why the task did not succeed.

Failure mode definitions:

- cap_open: the tube cap is open, loose, or not properly closed
- tube_drop: the tube is dropped
- tube_empty: the tube appears empty when it should contain material
- vortex_off: the vortexer is off, or there is no visible liquid movement while the tube is on the vortexer
- wrong_orientation: the tube, rack, or relevant object orientation is incorrect
- wrong_rack: the tube is placed in or associated with the wrong rack
- rack_flipped: the rack is flipped or inverted
- repeated_steps: the actor repeats one or more procedural steps
- other_failure: a visible failure is present but none of the listed modes fit

If the tube falls at any point before there has been enough vortexer contact to visibly move/agitate the liquid contents, choose `tube_drop`.

Use the videos as visual evidence.

Return exactly one JSON object, with no markdown fences and no extra text:

{
  "choice": "success",
  "outcome": "success",
  "primary_failure_mode": null,
  "failure_modes": [],
  "confidence": 0.0,
  "reasoning": "Brief visual evidence for the selected choice."
}

Output rules:

- `choice` must be exactly one of the allowed choices.
- If `choice` is `success`, set `outcome` to `success`, `primary_failure_mode` to null, and `failure_modes` to [].
- If `choice` is a failure mode, set `outcome` to `failure`, set `primary_failure_mode` to the same value as `choice`, and set `failure_modes` to a one-item array containing that same value.
- `confidence` must be a number from 0 to 1 indicating confidence in `choice`.
- `reasoning` should cite concise visual evidence, ideally under 30 words.
