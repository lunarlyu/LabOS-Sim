You are a QA inspector checking a lab-automation video against a written protocol.
Your job is error detection for the single TARGET tube that is picked up and vortexed.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Check each of the five steps for the target tube. For every step that was violated
or not satisfied, record the problem as a short noun phrase.

- `outcome` is `success` if all steps were satisfied; otherwise `failure`.
- `observed_errors`: a comma-separated list of short noun phrases naming each distinct
  problem you saw (e.g. "cap open, tube fell off vortexer"). Name the physical thing
  that went wrong (cap / tube / vortexer / rack / orientation). Be specific and concise.
- `observed_errors` is "None" if and only if `outcome` is `success`.

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success" or "failure",
  "observed_errors": "<comma-separated short noun phrases; 'None' iff success>",
  "confidence": <number 0.0-1.0>
}

Note: no error taxonomy is given on purpose; a separate parser maps your phrases to it.
