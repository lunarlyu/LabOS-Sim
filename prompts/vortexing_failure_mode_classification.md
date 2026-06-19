You are evaluating a lab automation video.

Task: classify whether the human successfully vortexed a tube.

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

Classify the scenario as success or as one or more failure modes. Use these failure modes:

- cap_open: the tube cap is open, loose, or not properly closed
- tube_drop: the tube is dropped
- tube_empty: the tube appears empty when it should contain material
- vortex_off: the vortexer is off or there is no visible liquid movement while the tube is on the vortexer
- wrong_orientation: the tube, rack, or relevant object orientation is incorrect
- wrong_rack: the tube is placed in or associated with the wrong rack
- rack_flipped: the rack is flipped or inverted
- repeated_steps: the actor repeats one or more procedural steps
- other_failure: a visible failure is present but none of the listed modes fit

If the tube falls at any point before there has been enough vortexer contact to visibly move/agitate the liquid contents, classify the scenario as failure and include `tube_drop`.

Use the videos as visual evidence.

Return exactly one JSON object, with no markdown fences and no extra text:

{
  "outcome": "success",
  "failure_modes": [],
  "primary_failure_mode": null,
  "confidence": 0.0,
  "rationale": "Brief visual evidence under 20 words."
}
