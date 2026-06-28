# Capability levels for VLM error detection

We frame the error-detection benchmark as three levels of increasing realism,
defined by how much scaffolding the model is given before it has to judge a lab
video.

**Easy level — taxonomy given.** The model is told the task (vortexing), the
definition of a successful execution, and the full list of failure modes. We ask
two things: can it separate success from failure videos, and can it correctly
name which failure mode(s) occurred? This isolates *recognition* ability with all
context handed over. (Prompts P1 and P3.)

**Middle level — protocol given, taxonomy withheld.** The model is given the task
and a written protocol, but *not* the list of failure modes; a separate LLM parser
then maps the model's free text onto the taxonomy for scoring. Two variants probe
how much the framing matters:

- **Strict / error-aware (P3 → P5 parser):** the model is told to detect errors
  and list them succinctly.
- **Free / error-unaware (P4 → P6 parser):** the model is only asked to *describe*
  the video against the protocol — it is not told this is an error-detection test
  — and the parser mines failure modes from its description. This tests whether a
  model notices errors unprompted.

**Hard level — task identification first.** This is the realistic deployment
setting. The model is not handed a single, pre-labeled operation; instead it sees
a live wet-lab video as part of a complete experiment protocol and must (1)
identify which operation the robot is currently performing, (2) infer or retrieve
the success definition for that operation, and (3) detect potential failures
against it. This mirrors how a deployed VLA would actually work — reason over the
whole protocol, localize the current step, then check it.

**Current limitation and scope.** Our present database supports only the easy and
middle levels. The hard level is not yet testable, for two reasons: we currently
have a single operation (vortexing) rather than a library of operations that would
make task identification non-trivial, and we do not yet have complete,
multi-step experiment protocols from which a per-operation success definition
could be retrieved. We therefore focus on the easy and middle levels for now.
Once we collect data spanning multiple operations and full experiment protocols,
the hard level — task identification followed by protocol-grounded failure
detection — becomes the natural next benchmark.
