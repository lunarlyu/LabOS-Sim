# Model roster & budget for the full-run design choice

Status: proposal, 2026-08-06. Companion to `M2_model.md` (§9 dataset sizing)
and `design_justification/` (media + prompt studies). Numbers below are
list-price estimates calibrated against measured run costs; treat them as
±30% planning figures, not quotes.

## 1. API routes available

| Route | Key owner | Access | Notes |
|---|---|---|---|
| OpenRouter | Luna (`_env.json`) | full catalog: **167 vision-capable models**; $15k/month limit | reports per-call `usage.cost` (exact billing); has Qwen-VL models |
| Arena (`https://api.preview.arena.ai/v1`) | Carrie (`ARENA_API_KEY` / `ANTHROPIC_AUTH_TOKEN`) | ~70 models incl. claude-\*, gemini-\*, gpt-4o/4.1/5.x, grok-4.3/4.5, deepseek-v4-\*, glm-5.x, kimi-k2.5–k3, qwen3.7-plus, o1/o3/o4-mini | OpenAI-compatible; vision verified for Gemini; **no Qwen-VL**; no provider-reported cost (token-table pricing only); does not expose context/modality metadata — probe before relying on a model |

Both routes were exercised end-to-end by the prompt-screen sanity run
(`design_justification/prompt_design_choice/screen_n80_independent_frames/`).

## 2. The binding constraint: input size

The selected media design (128 frames/view × 3 views @720 px, JPEG q=10)
produces **~420k input tokens per call**. That splits the catalog:

**Full design OK (context ≥ ~450k):**

| Model | ctx | $/M input (OpenRouter list) |
|---|---|---:|
| google/gemini-3.1-pro-preview (anchor) | 1M | 2.00 |
| google/gemini-3-flash-preview | 1M | 0.50 |
| google/gemini-3.5-flash / 3.6-flash | 1M | 1.50 |
| google/gemini-3.5-flash-lite | 1M | 0.30 |
| x-ai/grok-4.5 | 1M+ | 2.00 |
| x-ai/grok-4.3 / 4.20 | 1M+ | 1.25 |
| qwen/qwen3.8-max | 1M | 2.00 |
| qwen/qwen3.7-plus / 3.6-plus | 1M | 0.32 |
| moonshotai/kimi-k3 | 1M | 3.00 |
| openai/gpt-5.5-pro / 5.4-pro | ≥450k | 30.00 |
| anthropic/claude-opus-5-fast / 4.8-fast / fable-5 | ≥450k | 10.00 |
| meta/muse-spark-1.1 / 1.2 | 1M | 1.25 |
| thinkingmachines/inkling / inkling-small | 1M | 1.00 / 0.50 |

**Cannot take the full design** (200–400k ctx, or Anthropic's ~100-image
per-request cap): standard claude-opus-4.8/4.1, claude-sonnet, openai
gpt-5/5.2/o3, all mistral, most qwen-VL variants, small open models.

### Budget options for a cross-model suite

- **(a) Full design, big-context roster only** — keeps Luna's selected design
  intact but excludes standard Claude/GPT tiers.
- **(b) Reduced common budget for everyone** — e.g. 32 frames/view × 3 views
  = 96 images ≈ ~105k tokens/call: fits every candidate incl. Claude's image
  cap. Statistically cleanest for the SDT-IRT fit (identical inputs; ability
  differences attributable to the model, not the diet). Requires a small
  input-fidelity bridge study (128 vs 32 frames on Gemini) to quantify what
  the reduction costs.
- **(c) Two lanes (full for big-ctx, reduced for the rest)** — records budget
  as a covariate; worst option, confounds `alpha` with input budget in M2.

**Recommendation: (b)** if Claude/GPT standard tiers are wanted in the fit
(they are — see roster); otherwise (a).

## 3. Proposed roster (M ≈ 10) for the SDT-IRT fit

What M2 wants (see `M2_model.md`): per-model per-subtype precision comes from
clips, not from M, but every added model strengthens the shared subtype
parameters (`a_c`, `b_c`, `b_neg_c`) — and the fit needs *spread* in ability
and criterion across independent families.

| Tier | Model | Rationale | Route |
|---|---|---|---|
| Frontier | gemini-3.1-pro-preview | anchor; all existing design/prompt data | Arena/OR |
| Frontier | gpt-5.5 | second frontier family | Arena/OR |
| Frontier | claude-opus-4.8 | most criterion-distinctive model in prompt-ablation v1 | Arena (needs option b) |
| Frontier | grok-4.5 | 4th independent family; cheap | Arena/OR |
| Mid | gemini-3-flash-preview | free data from the prompt-ablation-v2 screen | Arena |
| Mid | claude-sonnet-5 | within-family scale pair for Opus | Arena |
| Mid | kimi-k3 | independent lab | Arena/OR |
| Mid | qwen3.8-max | independent lab, 1M ctx | OR |
| Budget | qwen3.7-plus or gemini-3.5-flash-lite | low-ability anchor that still responds | OR/Arena |
| Floor (optional) | qwen3-vl-8b | v1 data exists; degenerate responder (always `success`) — near-zero positive-channel information; keep at most one such model | OR only |

Within-family pairs (Opus/Sonnet, Pro/Flash) double as a validation figure:
`alpha` should track scale within a family.

### Roster details: price, context, native-video support, capability prior

OpenRouter list data (2026-08-07). "AA-intel" = Artificial Analysis
intelligence index as republished in the OpenRouter catalog (text-reasoning
composite; see "How ability tiers were assigned" below).

| Model | $/M in | $/M out | ctx | Native video input | AA-intel |
|---|---:|---:|---:|---|---:|
| gemini-3.1-pro-preview (anchor) | 2.00 | 12.00 | 1M | **yes** | 47.7 |
| gpt-5.5 | 5.00 | 30.00 | 1M | no — frames only | 56.3 |
| claude-opus-4.8 | 5.00 | 25.00 | 1M | no — frames only (+~100-image/request cap) | 57.3 |
| grok-4.5 | 2.00 | 6.00 | 500k | no — frames only | 55.8 |
| gemini-3-flash-preview | 0.50 | 3.00 | 1M | **yes** | — |
| claude-sonnet-5 | 2.00 | 10.00 | 1M | no — frames only (+image cap) | 55.3 |
| kimi-k3 | 3.00 | 15.00 | 1M | no — frames only | 59.7 |
| qwen3.8-max | 2.00 | 6.00 | 1M | **yes** | 58.1 |
| qwen3.7-plus | 0.32 | 1.28 | 1M | no — frames only | 39.4 |
| gemini-3.5-flash-lite | 0.30 | 2.50 | 1M | **yes** | 37.4 |
| qwen3-vl-8b (floor) | 0.12 | 0.45 | 262k | no — frames only | — |

(Catalog corrections vs. §2 above: claude-opus-4.8 and gpt-5.5 are 1M-context
on OpenRouter, so token count is NOT their binding constraint — Anthropic's
per-request image cap is, for the Claude tier.)

### Do any of them take the videos directly?

Only the Gemini family and qwen3.8-max advertise native video input. Even for
those, the benchmark still sends **frames, not video files**, for two reasons:

1. **Transport.** The pipeline ships media as base64 data-URIs through
   OpenRouter/Arena. Three raw 20 s clips are ~75–100 MB base64 — over
   practical request limits. Native video needs provider file-upload APIs
   (e.g. the google-genai File API; `requirements.txt` already carries the
   dependency), a per-provider code path we haven't built.
2. **Fairness.** The design-choice study's fairness profile feeds *identical
   inputs* to every model. If Gemini got true video (with motion) while
   Claude/GPT got 128 snapshots, ability differences would be confounded with
   input-pipeline differences — exactly what the SDT-IRT fit must not absorb
   into `alpha`. A "native-video lane" is a possible future condition for the
   video-capable subset, and would likely help motion subtypes
   (`vortex_off`, `tube_drop`), but it is a new design factor, not a default.

So: every roster model runs on the same trimmed-frame diet (128/view today;
fewer under budget option (b)). "Native video" is a capability note, not a
plan.

### How ability tiers were assigned

The tiers are **priors used to guarantee ability spread**, not measurements —
the IRT fit's `alpha` is the measurement. Sources, in decreasing weight:

1. **Our own runs.** The v1 pilot measured model behavior directly
   (claude-opus-4.8 most wording-sensitive; qwen3-vl-8b degenerate — always
   `success`; gemini success-biased on free tasks). The v2 screen measured the
   within-family gap (Flash P2 exact 0.175 vs Pro 0.30; Flash P1 failure
   recall 0.029).
2. **Within-family scale** (Pro > Flash, Opus > Sonnet) — the safest prior,
   and the roster includes both pairs precisely to *test* it via `alpha`.
3. **Public composite indices** (AA-intel above) — text-reasoning composites,
   NOT video-perception scores; note gemini-3.1-pro scores lowest of the
   frontier tier there while being our strongest measured video model. This
   mismatch is exactly why tier labels are held loosely.

Mis-ranking a model ex ante is harmless to the fit: M2 only needs the roster
to span a wide ability range, and surprises (a "mid" model fitting frontier
`alpha`) are findings, not errors.

## 4. Cost model

Measured anchor: Gemini 3.1 Pro at full design ≈ **$137 per prompt-task per
80 clips** (~36M input tokens; ~1.9× naive token math due to image billing
and retries) → ≈ **$410 per model** for the 3-prompt suite (P1+P2+P3, incl.
P5 parsing) on 80 clips.

Scaling rules of thumb:

- cost ∝ $/M input price (input dominates ~99% of tokens)
- cost ∝ clip count (254-clip catalog ≈ 3.2× the 80-clip selection)
- option (b) 96-image budget ≈ **~0.27×** the full-design cost

| Scenario | Est. cost |
|---|---:|
| 10-model roster, 80 clips, full design (a) | $2.5–4k |
| 10-model roster, 80 clips, reduced budget (b) | **$0.7–1.1k** |
| 10-model roster, 254 clips, reduced budget (b) | $2.2–3.5k |
| per extra frontier model (80 clips, b) | ~$110 |

### Prompt-caching lever (unverified, potentially ~2x on Gemini)

The 3 prompts re-send an identical media prefix (~99% of input tokens); the
per-task scripts run one full dataset pass per prompt, so the prefix always
misses the provider's implicit cache. `scripts/data_collection/run_vlm_suite.py`
instead sends each clip's prompts back-to-back (`runner.collect_suite`), which
on a provider-pinned route (`gemini_3_1_pro_or`) should let prompts 2–3 bill
the prefix at Gemini's cached rate: total input ≈ (1 + 2×0.25)/3 ≈ **0.5×**
if the discount is ~75%. Verify with `scripts/probe_prompt_cache.py` (1 clip
× 3 calls) before relying on it; unknowns are OpenRouter pass-through for
image-heavy prompts and whether per-task `response_format` breaks the prefix.

Probe results (2026-08-08, synthetic 128×3-frame payloads ≈ 419k prompt
tokens/call, `scripts/probe_prompt_cache.py --synthetic-frames`):

- **Arena**: no caching — a byte-identical repeat re-billed in full
  ($1.69/call).
- **Vertex, OpenAI-compatible endpoint** (ADC user creds, works via the
  existing adapter as `gemini_3_1_pro_vertex`): usage block carries no
  `prompt_tokens_details`, so cache hits are invisible; treat as uncached.
- **Vertex, native `generateContent`**: implicit caching fires ONLY on
  byte-identical payloads (417k/419k tokens cached, deterministic across
  repeated trials); a different trailing prompt got 0 cached even after the
  prefix had been sent five times. So the 3-prompt suite gains nothing from
  implicit caching — though retries of a failed call become ~free.
- **Vertex, explicit context caching**: WORKS across prompts — one
  `cachedContents` holding the media prefix (TTL 300s), then P1/P2/P3 each
  reported `cachedContentTokenCount` = 418,246 (99.9% of prompt).

Economics per clip, list-price math at the long-context tier (~$4/M effective
for >200k-token prompts — which also plausibly explains the "1.9×" factor in
§4: it matches the 2× long-context multiplier): no cache 3 × $1.68 ≈ $5.04;
explicit cache $1.68 (create) + 3 × ~$0.42 (cached ≈ 25%) + ~$0.15 storage
≈ **$3.1 → ~0.6×**, i.e. 500-clip 3-prompt Gemini suite ~$2.6k → ~$1.5k.
Creation-cost and cached-rate assumptions are list-price reads, pending a
billing-dashboard check.

**Implemented 2026-08-08** (live-tested end-to-end, 99% of prompt tokens
cached with structured output):

- `vertex_native` adapter (`src/labos_benchmark/adapters/vertex_native.py`):
  native `generateContent` + `cachedContents`, ADC auth with automatic token
  refresh, cached-token usage reporting; priced via `config/model_costs.json`
  (`cached_input_cost_per_1M`).
- `collect_suite` creates one context cache per clip when the model config
  sets `context_cache: {enabled: true}` (see `gemini_3_1_pro_vertex_native`),
  runs every prompt against it, deletes it after; falls back to full media on
  any cache failure.
- Other routes: `anthropic_cache_control: true` on an OpenAI-compatible model
  entry adds an Anthropic-style prompt-caching breakpoint after the media
  prefix (reads ~0.1×, writes 1.25× — pays off with ≥2 prompts/clip). Enabled
  for claude-opus-4.8 (matters under budget option (b)) and qwen3.8-max
  (Alibaba uses the same syntax through OpenRouter). Automatic prefix caching
  — no flag, clip-grouped order is the enabler — covers gpt-5.5 (reads
  0.25–0.5×), grok-4.5 and kimi-k3 (writes free, reads 0.25×). Per OpenRouter
  docs 2026-08; each route should get the 3-call probe before a big run —
  the Gemini implicit-caching lesson (identical-payload-only) shows documented
  ≠ actual. Roster-wide at 0.5× input, the 10-model 500-clip full-design
  suite drops roughly $16–25k → $8–13k.

Usage: `scripts/data_collection/run_vlm_suite.py --models
gemini_3_1_pro_vertex_native ...`. Combining with budget option (b)'s
32-frame diet drops prompts under 200k tokens back to the standard tier — a
multiplicative win.

## 5. Recommended sequence

1. Finish prompt-ablation v2 (in progress) → lock P1/P2 wording.
2. Decide budget option (a)/(b) with Luna; if (b), run the 128-vs-32-frame
   bridge condition on Gemini (~$140 + ~$40).
3. Pilot the M≈10 roster on the 80-clip selection at the agreed budget; fit
   M1/M2, check WAIC and whether `alpha` spread is resolvable.
4. Scale **clips** (not models) toward the 270/450 targets of `M2_model.md`
   §9 before making subtype-level claims.

## 6. Open questions

- Arena vision support for kimi/glm/deepseek is unprobed (1-pixel test per
  model before adding to roster).
- ~~Arena billing is not returned per call~~ resolved 2026-08-08: Arena DOES
  return `usage.cost` (+ `cost_details.upstream_inference_*`), so client.py
  cost accounting works there (source "provider"). Measured effective input
  price for gemini-3.1-pro-preview: **~$4.0/M — 2× the OpenRouter list price**
  (per-call cost ≈ OpenRouter's measured cost incl. its ~1.9× image-billing
  factor, so the routes land within pennies of each other per call). Arena
  showed no prompt-cache hits (see §4), so the caching lever is OR/direct-only.
- ~~`gpt-5.5` (non-pro) context window unverified~~ resolved: 1M on
  OpenRouter (roster details table) — full design fits.
