You are observing a lab-automation video. A reference protocol is provided for context.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

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

{
  "outcome": "success" or "failure",
  "description": "<step-by-step account: for each of the 5 steps, what you saw and whether it matched>",
  "confidence": <number 0.0-1.0>
}
