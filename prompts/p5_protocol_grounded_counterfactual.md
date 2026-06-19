You are evaluating a lab automation video against a written protocol.

Protocol:

1. Pick up a capped, non-empty tube.
2. Place the tube onto the vortexer.
3. Run the vortexer until visible liquid movement, spinning, or agitation occurs.
4. Remove the tube from the vortexer.
5. Place the tube into a suitable tube rack or holder that can hold it upright.

Question: Did the operator follow the protocol? Identify any deviations.

Return exactly one JSON object:

{
  "followed_protocol": true,
  "confidence": 0.0,
  "completed_steps": [
    "Step numbers or short names that were visibly completed."
  ],
  "deviations": [
    "Protocol deviations, if any."
  ],
  "counterfactual_correction": "What should have happened instead, if there was a deviation."
}
