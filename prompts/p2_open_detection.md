You are evaluating a lab automation video against a written protocol.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being
uncapped or empty is NOT a failure).

Vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Question: Was there any error in this video? If so, describe every error you see.

Do not restrict yourself to a fixed list of error types. Describe in your own
words each deviation you observe — there may be more than one, or none.

Output rules:

- Set `error_present` to `false` ONLY when you observe no error. In that case
  `observed_errors` must be empty (i.e. "None").
- Set `error_present` to `true` whenever there is at least one error, and
  describe every distinct error you see in `observed_errors`.

Return exactly one JSON object:

{
  "error_present": false,
  "confidence": 0.0,
  "observed_errors": [
    "One short free-text description per distinct error, if any."
  ],
  "reasoning": "Brief chronological visual evidence."
}

Note: this prompt is freeform on purpose (no error taxonomy is given). Its
output is converted into the standardized schema by the p6 parser.
