You are observing a lab-automation video. A reference protocol is provided for context.

Focus only on the single target tube that is picked up and vortexed. Other tubes in the scene are irrelevant: ignore their state (e.g. another tube being uncapped or empty is NOT a failure).

Reference vortexing protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Describe, in your own words and in chronological order, exactly what happens to the
target tube. Be concrete and detailed about each action you see. As you narrate, note
anything that looks different from the reference protocol — however small — including
the state of the cap, whether the tube has liquid, whether the vortexer actually runs,
the tube's orientation, and where and how the tube ends up. Then state whether, from
your own description, the operator followed the protocol.

Return exactly one JSON object. Replace every value with your own:

{
  "outcome": "success" or "failure",
  "description": "<detailed chronological account of what happens with the target tube>",
  "confidence": <number 0.0-1.0>
}
