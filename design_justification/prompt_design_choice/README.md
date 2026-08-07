# Prompt design choice

One study in two stages: does any hypothesis-driven rewording of the
evaluation prompts (P1–P6) beat the committed wording ("B")? The narrative
version lives in `../design_choices_experiment/prompt_experiments.md`.

| Stage | Folder | Setup | Outcome |
|---|---|---|---|
| 1. Pilot (2026-07-08) | `pilot_n10_contact_sheets/` | B/V1/V2 per prompt × 3 models × 10 clips, contact-sheet media | P4-V2 and P6-V2 adopted into `prompts/`; P1-V1/P2-V1 "wins" held back as within n=10 noise |
| 2. Screen (2026-08-07) | `screen_n80_independent_frames/` | Held-back variants × Gemini 3 Flash × the 80-clip design-choice selection, final independent-frame media | P1-V1 and P2-V1 failed to replicate — committed prompts stand; P2-V2 the lone (sub-noise) stage-2 candidate |

The pilot folder is also the single source of the variant prompt files
(`pilot_n10_contact_sheets/variants/`), which the screen runner reads
directly — do not delete it while the screen remains reproducible. Each
stage keeps its own runs under `<stage>/runs/` (media caches gitignored).

Bottom line: the committed `prompts/` wording is the evidenced choice at
both n=10 (multi-model) and n=80 (Gemini family). Open item: an optional
~$137 confirmation of P2-V2 on the anchor model
(`screen_n80_independent_frames/README.md`, Results section).
