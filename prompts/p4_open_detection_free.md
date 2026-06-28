You are observing a lab automation video. A reference protocol for the task is
provided below for context.

Focus your attention on the single target tube that is picked up and vortexed.
Other tubes in the scene are not relevant.

Reference vortexing protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Question: In your own words, describe what happens in the video with the target
tube, step by step, comparing what you see against the reference protocol. Then
state whether the operator followed the protocol.

Instructions:

- `description` is your own free-text account of what happens in the video. Always
  provide it, whether or not everything looked correct — describe the actions you
  see and note anything that differs from the reference protocol.
- Set `outcome` to `success` if, from what you describe, the operator followed
  the protocol; otherwise `failure`.

Return exactly one JSON object:

{
  "outcome": "success",
  "description": "A chronological account of what happens with the target tube.",
  "confidence": 0.0
}
