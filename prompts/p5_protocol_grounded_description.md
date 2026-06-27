You are evaluating a lab automation video against a written protocol.

Protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Question: Describe what happened in the video, then judge whether the operator
followed the protocol and identify every deviation.

You are NOT given a list of error types — describe each deviation in your own
words, grounded in the protocol steps above. There may be more than one
deviation, or none.

Return exactly one JSON object:

{
  "summary": "Brief chronological description of what happened.",
  "followed_protocol": true,
  "confidence": 0.0,
  "completed_steps": [
    "Step numbers or short names that were visibly completed."
  ],
  "deviations": [
    "One free-text description per protocol deviation, if any."
  ],
  "reasoning": "Brief visual evidence."
}

Note: this prompt is freeform on purpose (no error taxonomy is given). Its
output is converted into the standardized schema by the p6 parser. It merges the
former p4 (free-form description) and p5 (protocol-grounded) prompts.
