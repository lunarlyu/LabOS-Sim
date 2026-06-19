# Model Suite Selection

Updated: 2026-06-19

Source: OpenRouter `/api/v1/models` catalog lookup on 2026-06-19.

## Headline Configs

| Family | OpenRouter ID | Catalog modality | Benchmark media mode | Config |
|---|---|---|---|---|
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | `text+image+file+audio+video->text` | direct video, 1080px/30fps | `single_choice_full_gemini_3_1_pro_standard_video.json` |
| GPT-5.5 | `openai/gpt-5.5` | `text+image+file->text` | image contact sheets | `single_choice_full_gpt_5_5_standard_contact_sheet.json` |
| Claude Opus 4.8 | `anthropic/claude-opus-4.8` | `text+image+file->text` | image contact sheets | `single_choice_full_claude_opus_4_8_default_contact_sheet.json` |
| Qwen3-VL-8B | `qwen/qwen3-vl-8b-instruct` | `text+image->text` | image contact sheets | `single_choice_full_qwen3_vl_8b_official_contact_sheet.json` |

## Subset / Budget Configs

| Family | OpenRouter ID | Mode | Config |
|---|---|---|---|
| Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` | vendor default mode on 20-sample subset | `single_choice_subset20_gemini_3_1_pro_default_video.json` |
| GPT-5.5 Pro | `openai/gpt-5.5-pro` | vendor default mode on 20-sample subset, budget permitting | `single_choice_subset20_gpt_5_5_pro_standard_contact_sheet.json` |
| Claude Opus 4.8 | `anthropic/claude-opus-4.8` | vendor default mode on 20-sample subset | `single_choice_subset20_claude_opus_4_8_default_contact_sheet.json` |
| GPT-5.5 | `openai/gpt-5.5` | 5-sample smoke | `single_choice_smoke_gpt_5_5_standard_contact_sheet.json` |

## Default-Mode Policy From Screenshot

- Frontier API models (`GPT-5.5`, `Claude Opus 4.8`, `Gemini 3.1 Pro`): use vendor defaults for reasoning/mode.
- Temperature: use `temperature=0` for Gemini and Claude. GPT configs omit `temperature` so GPT uses its API default.
- Qwen3-VL: use Qwen official/default visual settings rather than VLMEvalKit-specific bumped pixel values.
- Cosmos Reason 2: reasoning flag should be ON once the exact runnable endpoint is available.
- Cosmos Reason 2 fps: use 4 fps if it supports direct video and clips are short enough.
- Reasoning strategy: Strategy A, vendor defaults, documented in benchmark notes.
- Cross-model video sampling: use uniform sampling, about 16-32 frames per clip. Current contact-sheet configs use 1 fps into a 4x8 sheet per camera video, capped at 32 frames per clip.

## Cosmos Reason 2

OpenRouter did not return any `cosmo` or `cosmos` model IDs in the catalog. I did not create a runnable Cosmos JSON config because guessing an ID would make the benchmark non-reproducible. See `cosmos_reason_2_PENDING_MODEL_ID.md` for the intended defaults once an exact endpoint/model ID is available.

## Media Notes

GPT-5.5, Claude Opus 4.8, and Qwen3-VL do not advertise native video input in the OpenRouter catalog. Their configs use `image_contact_sheet`, which converts each selected camera video into a JPEG contact sheet using:

- max width: 720px
- sample rate: 1 fps
- layout: 4 columns by 8 rows
- JPEG quality: 3

Gemini 3.1 Pro advertises video input and keeps the direct `1080px/30fps` video profile.
