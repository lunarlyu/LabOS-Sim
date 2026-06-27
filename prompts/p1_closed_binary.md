You are evaluating a lab automation video.

Question: Was this vortexing task performed correctly? Answer success or failure.

A correct execution has all of these properties:

- A tube is picked up.
- The tube is placed onto a vortexer.
- The vortexer runs, meaning visible movement, spinning, or agitation of the liquid contents is observed.
- The tube is taken off the vortexer.
- The tube is placed into a tube holder or test tube rack.
- The tube is non-empty.
- The vortexed tube can be any tube in the scene.
- The tube has a cap on it.
- The rack or holder can actually hold the tube.

Set `outcome` to `success` only if every property holds; otherwise `failure`.
`failure_modes` is always empty for this prompt (it does not classify subtypes).

Return exactly one JSON object:

{
  "outcome": "success",
  "failure_modes": [],
  "confidence": 0.0,
  "reasoning": "Brief visual evidence."
}
