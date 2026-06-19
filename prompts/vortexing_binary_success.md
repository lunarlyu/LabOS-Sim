You are evaluating a lab automation video.

Task: determine whether the human successfully vortexed a tube.

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

Determine whether the vortexing task succeeded. A failure includes any missing success criterion, such as an empty tube, missing cap, dropped tube, no visible liquid movement while on the vortexer, wrong or unusable rack/holder, flipped rack, wrong orientation, repeated procedural issue, or another visible procedural problem.

If the tube falls at any point before there has been enough vortexer contact to visibly move/agitate the liquid contents, classify the task as a failure.

Use the videos as visual evidence.

Return exactly one JSON object, with no markdown fences and no extra text:

{
  "success": true,
  "confidence": 0.0,
  "observed_failure": "",
  "rationale": "Brief visual evidence under 20 words."
}
