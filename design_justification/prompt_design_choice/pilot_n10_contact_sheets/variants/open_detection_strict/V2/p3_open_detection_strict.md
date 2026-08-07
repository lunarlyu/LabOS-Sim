You are evaluating a lab-automation video against a written protocol. Detect any
errors in the vortexing of the single TARGET tube.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

For each problem you see, describe it by (a) which object it concerns — cap, the tube
itself, the vortexer, or the destination rack/holder — and (b) what was wrong with it.
Examples of the style expected: "cap not secured", "tube dropped on the bench",
"vortexer never turned on", "tube placed sideways", "rack upside-down", "tube empty".

- `outcome` is `success` only when the protocol was fully followed; otherwise `failure`.
- `observed_errors`: comma-separated short noun phrases, one per distinct problem;
  "None" if and only if `outcome` is `success`.

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success" or "failure",
  "observed_errors": "<comma-separated short noun phrases; 'None' iff success>",
  "confidence": <number 0.0-1.0>
}

Note: no error taxonomy is given on purpose; a separate parser maps your phrases to it.
