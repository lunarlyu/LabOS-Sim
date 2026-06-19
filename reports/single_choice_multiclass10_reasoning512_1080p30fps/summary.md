# Single-Choice Multiclass 10-Sample Benchmark

Updated: 2026-06-18

Run: `runs/single_choice_multiclass10_reasoning512_1080p30fps_001`

MiniMax retries:

- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry1`
- `runs/single_choice_multiclass10_reasoning512_1080p30fps_minimax_retry2`

Config: `configs/benchmarks/single_choice_multiclass_10_medium_reasoning_1080p30fps.json`

Dataset: `metadata/real_human_samples_no_multiple.json`, which removes the 3
ambiguous `multiple` condition samples from the benchmark metadata.

Reasoning setting: OpenRouter rejected sending both `reasoning.effort` and
`reasoning.max_tokens`, so the final run used `reasoning.max_tokens=512` with
`reasoning.exclude=true`. This gives a bounded medium-sized thinking budget
while keeping hidden reasoning out of the model output.

## Aggregate Results

| Model | Model ID | Completed | Parse Errors | Parser-Recovered | Exact Choice Acc. | Outcome Acc. | Avg Conf. | Reasoning Tokens | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MiniMax | minimax/minimax-m3 | 9/10 | 1 | 2 | 10.0% | 20.0% | 0.87 | 8428 | $0.069408 |
| Gemini Flash | google/gemini-3.5-flash | 10/10 | 0 | 0 | 50.0% | 70.0% | 0.96 | 3656 | $0.095196 |
| Gemini Pro | google/gemini-3.1-pro-preview-20260219 | 10/10 | 0 | 0 | 40.0% | 70.0% | 0.95 | 3623 | $0.125644 |
| Qwen | qwen/qwen3.6-plus | 10/10 | 0 | 0 | 30.0% | 50.0% | 0.94 | 5120 | $0.104253 |

## Per-Sample Predictions

| Model | Sample | Expected | Predicted | Exact? | Confidence | Status | Parser-Recovered | Reasoning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MiniMax | real_human_carrie_00_success_success_01_clean | success | vortex_off | no | 0.7 | completed | yes | Tube placed on vortexer but no visible liquid movement or spinning observed; vortexer appears off. |
| MiniMax | real_human_carrie_00_success_success_02_clean | success | vortex_off | no | 0.9 | completed | no | The person places the tube on the vortexer and immediately removes it; there is no visible liquid movement or spinning, indicating the vortexer was not activated. |
| MiniMax | real_human_carrie_00_success_success_03_clean | success | vortex_off | no | 0.85 | completed | no | Tube is picked up, placed on vortexer, and returned to rack, but no visible liquid agitation/spinning occurs while tube is on vortexer. |
| MiniMax | real_human_carrie_01_cap_open_fail_cap_loose_01 | cap_open | success | no | 0.99 | completed | no | The person picked up a capped, non-empty tube, placed it on the vortexer, the vortexer visibly agitated the liquid, and returned the tube to the rack. |
| MiniMax | real_human_carrie_02_tube_drop_fail_tube_drop_01 | tube_drop | vortex_off | no | 0.95 | completed | yes | The person places the tube on the vortexer, but the liquid inside remains completely still, indicating the vortexer was not turned on. |
| MiniMax | real_human_carrie_03_tube_empty_fail_tube_empty_01 | tube_empty |  | no |  | parse_error | no |  |
| MiniMax | real_human_carrie_04_vortex_off_fail_vortex_off_01 | vortex_off | success | no | 0.85 | completed | no | Person picks up capped tube with pink liquid from orange rack, places it on vortexer, presses down to activate (visible agitation), removes it, and returns it to the rack. |
| MiniMax | real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01 | wrong_orientation | success | no | 0.85 | completed | no | Person picks up capped tube with pink liquid from orange rack, places it on vortexer, presses down (vortexer runs with visible agitation), removes tube, and returns it to the orange rack. |
| MiniMax | real_human_carrie_06_wrong_rack_fail_wrong_rack_01 | wrong_rack | success | no | 0.95 | completed | no | Tube with pink liquid picked up, placed on vortexer (visible agitation), removed, and placed into red rack. Cap is on, tube is non-empty, and fits the rack. |
| MiniMax | real_human_carrie_07_rack_flipped_fail_rack_flipped_01 | rack_flipped | rack_flipped | yes | 0.82 | completed | no | The orange tube rack is clearly knocked over on its side with the tube lying on the table, visible across all camera angles. No vortexing occurred. |
| Gemini Flash | real_human_carrie_00_success_success_01_clean | success | other_failure | no | 0.9 | completed | no | The tube is left on the vortexer and not returned to a tube rack, failing the required sequence. |
| Gemini Flash | real_human_carrie_00_success_success_02_clean | success | success | yes | 0.95 | completed | no | The operator successfully picks up the capped tube from the blue rack, vortexes it with visible liquid agitation, and places it back into the rack. |
| Gemini Flash | real_human_carrie_00_success_success_03_clean | success | success | yes | 1.0 | completed | no | The operator successfully picks up the tube, vortexes it with visible liquid agitation, and places it back into the rack. |
| Gemini Flash | real_human_carrie_01_cap_open_fail_cap_loose_01 | cap_open | cap_open | yes | 0.95 | completed | no | The tube is vortexed without its cap, which is visibly lying on the table next to the rack. |
| Gemini Flash | real_human_carrie_02_tube_drop_fail_tube_drop_01 | tube_drop | vortex_off | no | 0.95 | completed | no | The actor placed the tube on the vortexer, but it did not run because it was turned off. She then placed the tube on the table and turned the vortexer on. |
| Gemini Flash | real_human_carrie_03_tube_empty_fail_tube_empty_01 | tube_empty | vortex_off | no | 0.95 | completed | no | The tube is placed on the vortexer, but the vortexer does not turn on and there is no visible agitation of the liquid. |
| Gemini Flash | real_human_carrie_04_vortex_off_fail_vortex_off_01 | vortex_off | vortex_off | yes | 0.95 | completed | no | The tube is placed on the vortexer, but there is no visible agitation or movement of the liquid, indicating the vortexer is off. |
| Gemini Flash | real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01 | wrong_orientation | success | no | 1.0 | completed | no | The operator successfully picks up the tube, turns on the vortexer, vortexes the liquid, and returns the tube to the rack. |
| Gemini Flash | real_human_carrie_06_wrong_rack_fail_wrong_rack_01 | wrong_rack | success | no | 1.0 | completed | no | The tube is successfully picked up, vortexed with visible liquid agitation, and placed back into a rack. |
| Gemini Flash | real_human_carrie_07_rack_flipped_fail_rack_flipped_01 | rack_flipped | rack_flipped | yes | 0.95 | completed | no | The orange tube rack is knocked over and flipped onto its side at the beginning of the video. |
| Gemini Pro | real_human_carrie_00_success_success_01_clean | success | success | yes | 1.0 | completed | no | The tube is picked up, successfully vortexed with visible liquid agitation, and returned to the rack. |
| Gemini Pro | real_human_carrie_00_success_success_02_clean | success | success | yes | 1.0 | completed | no | The person successfully picks up a capped tube containing liquid, vortexes it with visible liquid agitation, and returns it to the rack. |
| Gemini Pro | real_human_carrie_00_success_success_03_clean | success | success | yes | 1.0 | completed | no | The person successfully picks up a capped, non-empty tube, places it on the vortexer which visibly agitates the liquid, and returns it to the rack. |
| Gemini Pro | real_human_carrie_01_cap_open_fail_cap_loose_01 | cap_open | tube_empty | no | 0.9 | completed | no | The tube picked up and placed on the vortexer is visibly empty. |
| Gemini Pro | real_human_carrie_02_tube_drop_fail_tube_drop_01 | tube_drop | other_failure | no | 0.9 | completed | no | The tube is placed on the table rather than into a tube holder or rack. |
| Gemini Pro | real_human_carrie_03_tube_empty_fail_tube_empty_01 | tube_empty | success | no | 0.85 | completed | no | The actor successfully picks up a capped, non-empty tube, vortexes it with visible liquid agitation, and returns it to the rack. |
| Gemini Pro | real_human_carrie_04_vortex_off_fail_vortex_off_01 | vortex_off | success | no | 1.0 | completed | no | The tube is picked up, successfully vortexed with visible liquid agitation, and placed back into the rack. |
| Gemini Pro | real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01 | wrong_orientation | success | no | 1.0 | completed | no | The person successfully picks up a capped, non-empty tube, vortexes it with visible liquid agitation, and returns it to the rack. |
| Gemini Pro | real_human_carrie_06_wrong_rack_fail_wrong_rack_01 | wrong_rack | vortex_off | no | 0.95 | completed | no | The tube is placed on the vortexer, but the pink liquid inside remains completely still, indicating the vortexer is off. |
| Gemini Pro | real_human_carrie_07_rack_flipped_fail_rack_flipped_01 | rack_flipped | rack_flipped | yes | 0.9 | completed | no | The orange tube rack is lying on its side (flipped) on the table, and no task execution occurs. |
| Qwen | real_human_carrie_00_success_success_01_clean | success | success | yes | 0.95 | completed | no | The person picks up a tube, places it on the vortexer, holds it to activate mixing, and returns it to the rack. |
| Qwen | real_human_carrie_00_success_success_02_clean | success | success | yes | 0.95 | completed | no | The person picks up a capped tube, places it on the vortexer, holds it to activate mixing, and returns it to the rack. |
| Qwen | real_human_carrie_00_success_success_03_clean | success | success | yes | 0.9 | completed | no | The person picks up a tube, places it on the vortexer, holds it to activate mixing, and returns it to the rack. |
| Qwen | real_human_carrie_01_cap_open_fail_cap_loose_01 | cap_open | success | no | 0.95 | completed | no | The person picks up a capped tube, places it on the vortexer, activates it (visible shaking/liquid movement), removes it, and places it back in the rack. |
| Qwen | real_human_carrie_02_tube_drop_fail_tube_drop_01 | tube_drop | vortex_off | no | 0.9 | completed | no | The tube is placed on the vortexer for a very short duration with no visible liquid agitation or spinning, indicating the vortexer was not active. |
| Qwen | real_human_carrie_03_tube_empty_fail_tube_empty_01 | tube_empty | success | no | 0.95 | completed | no | The person picks up a tube, places it on the vortexer, holds it to activate mixing, and returns it to the rack. All success criteria are met. |
| Qwen | real_human_carrie_04_vortex_off_fail_vortex_off_01 | vortex_off | success | no | 0.95 | completed | no | The person picks up a capped tube with pink liquid, places it on the vortexer to mix, and returns it to the rack. |
| Qwen | real_human_carrie_05_wrong_orientation_fail_wrong_orientation_01 | wrong_orientation | success | no | 1.0 | completed | no | The person picks up a capped tube with pink liquid, places it on the vortexer where the liquid visibly agitates, and returns it to the rack. |
| Qwen | real_human_carrie_06_wrong_rack_fail_wrong_rack_01 | wrong_rack | success | no | 0.95 | completed | no | The person picks up a capped tube with pink liquid, places it on the vortexer where the liquid agitates, removes it, and places it securely into a rack. |
| Qwen | real_human_carrie_07_rack_flipped_fail_rack_flipped_01 | rack_flipped | tube_drop | no | 0.95 | completed | no | A person knocks over the orange rack, causing the tube to fall out onto the bench before any vortexing occurs. |
