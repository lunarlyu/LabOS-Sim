You are evaluating a lab automation video.

Question: Was there any error in this video? If so, describe every error you see.

Use the correct vortexing protocol as the reference: pick up a capped,
non-empty tube, place it on the vortexer, visibly vortex/agitate the liquid,
remove the tube, and place it into a suitable tube rack or holder.

Do not restrict yourself to a fixed list of error types. Describe in your own
words each deviation you observe — there may be more than one, or none. If the
video looks correct, say so.

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
