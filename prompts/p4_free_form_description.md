<!--
DEPRECATED (2026-06-26): merged into p5_protocol_grounded_description.md.
p4 (free-form description) and the former p5 (protocol-grounded) overlapped;
they are now a single middle-level prompt. Use p5_protocol_grounded_description.md.
-->

You are evaluating a lab automation video.

Question: Describe what happened, including any deviation from correct
execution.

Use the correct vortexing protocol as the reference: pick up a capped,
non-empty tube, place it on the vortexer, visibly vortex/agitate the liquid,
remove the tube, and place it into a suitable tube rack or holder.

Return exactly one JSON object:

{
  "summary": "Brief chronological description of what happened.",
  "deviations": [
    "Deviation from correct execution, if any."
  ],
  "confidence": 0.0
}
