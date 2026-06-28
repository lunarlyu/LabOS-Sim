You are evaluating a lab automation video.

Question: Was this vortexing task performed correctly? Answer success or failure.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being
uncapped or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

(The target tube can be any tube in the scene; whichever tube is vortexed is the
one you evaluate.)

Set `outcome` to `success` only if every step of the protocol is completed for
the target tube; otherwise `failure`.
`failure_modes` is always empty for this prompt (it does not classify subtypes).

Return exactly one JSON object:

{
  "outcome": "success",
  "failure_modes": [],
  "confidence": 0.0,
  "reasoning": "Brief visual evidence."
}
