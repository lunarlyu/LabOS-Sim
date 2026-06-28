You are evaluating a lab automation video against a written protocol. Your job is
error detection: decide whether the vortexing was done correctly and, if not,
list what went wrong.

Focus only on the single target tube that is picked up and vortexed. Other tubes
in the scene are irrelevant: ignore their state (e.g. another tube being uncapped
or empty is NOT a failure).

Correct vortexing protocol (evaluate only the single target tube being vortexed):

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Question: Was the protocol followed, and if not, what errors occurred?

Instructions:

- Set `outcome` to `success` if the protocol was followed with no error;
  otherwise `failure`.
- `observed_errors` is a single, succinct, comma-separated list of the distinct
  errors you observe (e.g. "cap is open, tube dropped"). Be concise — short noun
  phrases, not sentences.
- `observed_errors` must be `"None"` if and only if `outcome` is `success`;
  it must list at least one error whenever `outcome` is `failure`.

Return exactly one JSON object:

{
  "outcome": "success",
  "observed_errors": "None",
  "confidence": 0.0
}

Note: this prompt gives no error taxonomy on purpose; its output is mapped to the
standardized schema by the p5 parser.
