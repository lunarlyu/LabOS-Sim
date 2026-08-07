You are evaluating a lab-automation video for correct vortexing of the single TARGET tube.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Check each step in order for the target tube and note whether it was satisfied:
(1) tube was capped and non-empty when picked up; (2) it was placed on the vortexer;
(3) the vortexer visibly ran (agitation/spinning/liquid movement) with the tube on it;
(4) the tube was removed; (5) it was placed upright into a holder that can support it.

If ANY step is violated or clearly not satisfied, the outcome is `failure`. The run is
`success` only when all five steps are satisfied for the target tube.

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success" or "failure",
  "failure_modes": [],
  "confidence": <number 0.0-1.0: your certainty in the outcome>,
  "reasoning": "<one or two sentences citing the specific visible evidence>"
}
