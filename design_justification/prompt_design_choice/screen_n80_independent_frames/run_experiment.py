#!/usr/bin/env python3
"""Prompt-ablation v2: confirm held-back prompt variants on the 80-clip
design-choice selection, under the final media design.

The July 8 prompt pilot (../pilot_n10_contact_sheets/) ran on 10 clips with the
contact-sheet media pipeline. The media design has since moved to independent
frames, which changed P2's failure mode from mode-collapse to under-flagging,
so the held-back winners need confirmation under the final design before
adoption.

Fixed to the design-choice selected_design: Gemini 3.1 Pro via OpenRouter,
independent frames, 128/view, front+left+right, 720 px, JPEG q=10, 2048
tokens, temperature 0, 5 retries. The B (baseline-prompt) arm is NOT re-run:
it is the completed design-choice baseline run
../eval_design_choices/raw/gemini31pro_multiframe_design_02_baseline_*.

Arms (see README.md for hypotheses and cost):
  p1_v1  P1 high-specificity wording          (~$140 VLM)
  p2_v1  P2 high-precision wording            (~$140 VLM)
  p2_v2  P2 high-recall scan-every-subtype    (~$140 VLM)
  p5_v2  P5 synonym-guide parser re-scoring the committed baseline P3 output
         (parser-only, ~$1; no VLM calls)

Variant prompt files are read from ../pilot_n10_contact_sheets/variants/ (single source
of truth). Prompt loading is redirected in-process; committed prompts/ and
src/ are untouched.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from labos_benchmark import runner  # noqa: E402
from labos_benchmark import prompts as P  # noqa: E402

# Screening model (cheap, same Gemini family as the anchor) vs. anchor model.
# The anchor's B arm is the completed design-choice baseline run (OpenRouter);
# the screening model has no committed baseline, so B arms run alongside its
# variants and the whole screening stage is provider-self-consistent.
MODEL_TRANSPORT = {
    "gemini_3_1_pro": {
        "est_cost_per_arm": 137,
        "provider_model_id": {"openrouter": "google/gemini-3.1-pro-preview",
                              "arena": "gemini-3.1-pro-preview"},
    },
    "gemini_3_flash": {
        "est_cost_per_arm": 35,
        "provider_model_id": {"openrouter": "google/gemini-3-flash-preview",
                              "arena": "gemini-3-flash-preview"},
        # Flash is a reasoning model: its thinking tokens share the completion
        # budget, and the design condition's 2048 truncates P2's JSON mid-field
        # (observed in the sanity run: finish_reason=length on all 6 retries).
        # All Flash arms share this cap, so the within-screen comparison holds.
        "max_completion_tokens": 8192,
    },
}
DEFAULT_MODEL = "gemini_3_flash"
PROVIDERS = {
    # Luna's OpenRouter key: base URL from OPENROUTER_BASE_URL (_env.json).
    "openrouter": {"base_url_env": "OPENROUTER_BASE_URL",
                   "api_key_env": "OPENROUTER_API_KEY"},
    # Carrie's Arena key: OpenAI-compatible endpoint, Bearer auth. If
    # ARENA_API_KEY is unset, main() falls back to ANTHROPIC_AUTH_TOKEN
    # (the shell already carries the Arena token under that name).
    "arena": {"base_url": "https://api.preview.arena.ai/v1",
              "api_key_env": "ARENA_API_KEY"},
}
DEFAULT_PROVIDER = "arena"
PARSER_MODEL = "gpt_5_5_parser"  # parser calls always go through OpenRouter
SAMPLES_PER_TYPE = 10
N_CLASSES = 8
EXPECTED_SAMPLES = SAMPLES_PER_TYPE * N_CLASSES
SELECTION_MANIFEST = (
    HERE.parents[1] / "design_choices_experiment/selected_samples_10_per_type.csv"
)
VARIANTS = HERE.parent / "pilot_n10_contact_sheets/variants"
RUNS_ROOT = HERE / "runs"
DESIGN_CACHE = HERE.parents[1] / "eval_design_choices/.media_cache"

# Completed design-choice baseline run (gemini_3_1_pro): serves as the B arm
# for P1/P2 when running the anchor model, and as the P3 source for the p5_v2
# parser arm (parser scoring is VLM-independent).
BASELINE_RUN = "gemini31pro_multiframe_design_02_baseline_f128_views3_tok2048_res720"
BASELINE_P3_DIR = (
    HERE.parents[1] / "eval_design_choices/raw" / BASELINE_RUN
    / "vortex_open_detection_strict" / "gemini_3_1_pro"
)

# selected_design from ../design_choices_experiment/design_matrix.yaml
CONDITION = {
    "frame_count": 128,
    "views": ["front", "left", "right"],
    "tokens": 2048,
    "resolution": 720,
}

FILES = {
    "closed_binary": "p1_closed_binary.md",
    "multilabel_classification": "p2_multilabel_classification.md",
    "open_detection_strict_parser": "p5_open_detection_strict_parser.md",
}

VLM_ARMS = {
    # B arms use the committed prompts/ (no redirection). They are skipped for
    # gemini_3_1_pro, whose B arm is the committed design-choice baseline run.
    "p1_b": {"ptype": "closed_binary", "task": "vortex_closed_binary", "cand": None},
    "p2_b": {"ptype": "multilabel_classification",
             "task": "vortex_multilabel_classification", "cand": None},
    "p1_v1": {"ptype": "closed_binary", "task": "vortex_closed_binary", "cand": "V1"},
    "p2_v1": {"ptype": "multilabel_classification",
              "task": "vortex_multilabel_classification", "cand": "V1"},
    "p2_v2": {"ptype": "multilabel_classification",
              "task": "vortex_multilabel_classification", "cand": "V2"},
}
PARSER_ARMS = {
    "p5_v2": {"ptype": "open_detection_strict_parser",
              "task": "vortex_open_detection_strict_parser", "cand": "V2"},
}
ALL_ARMS = {**VLM_ARMS, **PARSER_ARMS}

# ---- prompt-loading redirection (same mechanism as ../prompt_ablation) ----- #
ACTIVE: dict[str, str] = {}  # ptype -> variant file path


def _patched_get_prompt_path(task_name, prompts_dir=None):
    ptype = P.prompt_type_of(task_name)
    if ptype in ACTIVE:
        return Path(ACTIVE[ptype])
    return P.PROMPTS_DIR / P.PROMPT_FILES[ptype] if hasattr(P, "PROMPT_FILES") \
        else _ORIG_GET_PROMPT_PATH(task_name, prompts_dir)


_ORIG_GET_PROMPT_PATH = P.get_prompt_path
P.get_prompt_path = _patched_get_prompt_path


def set_active(ptype: str, cand: str) -> None:
    path = VARIANTS / ptype / cand / FILES[ptype]
    if not path.is_file():
        raise SystemExit(f"variant prompt not found: {path}")
    ACTIVE[ptype] = str(path)


def variant_path(arm: str) -> Path | None:
    spec = ALL_ARMS[arm]
    if spec["cand"] is None:  # B arm: committed prompts/, no redirection
        return None
    return VARIANTS / spec["ptype"] / spec["cand"] / FILES[spec["ptype"]]


# ---- config: pinned to the design-choice baseline condition ---------------- #
def build_cfg(base: dict, model: str, provider_name: str) -> dict:
    cfg = copy.deepcopy(base)
    defaults = cfg.setdefault("defaults", {})
    call = defaults.setdefault("call", {})
    call["max_retries"] = 5
    call["max_completion_tokens"] = CONDITION["tokens"]
    media = defaults.setdefault("media", {})
    media["input_type"] = "image_frames"
    preprocess = media.setdefault("preprocess", {})
    frames = preprocess.setdefault("frames", {})
    frames.update({
        "frame_count": CONDITION["frame_count"],
        "cap_at_source": False,
        "max_width": CONDITION["resolution"],
        "quality": 10,
    })
    # Same transport pinning as the design-choice runner: keep the experiment
    # independent of later registry edits. The screening model is defined here
    # rather than in config/models.yaml so this experiment stays self-contained.
    provider = PROVIDERS[provider_name]
    max_tokens = MODEL_TRANSPORT[model].get("max_completion_tokens", CONDITION["tokens"])
    call["max_completion_tokens"] = max_tokens
    cfg["models"].setdefault(model, {"role": "vlm"})
    cfg["models"][model].update({
        "adapter": "gemini",
        "provider_model_id": MODEL_TRANSPORT[model]["provider_model_id"][provider_name],
        "api_style": "openai_compatible",
        "media_transport": "data_uri",
        "temperature": 0,
        "max_completion_tokens": max_tokens,
        "timeout_s": 180,
        **({"base_url": provider["base_url"]} if "base_url" in provider
           else {"base_url_env": provider["base_url_env"]}),
        "api_key_env": provider["api_key_env"],
    })
    # Arena does not return provider-reported usage.cost (OpenRouter does), so
    # give the cost table the bare model ids at OpenRouter list prices as an
    # approximation; cost_source will show "table" for these calls.
    costs = cfg.setdefault("model_costs", {})
    costs.setdefault("gemini-3-flash-preview",
                     {"input_cost_per_1M": 0.5, "output_cost_per_1M": 3.0})
    costs.setdefault("gemini-3.1-pro-preview",
                     {"input_cost_per_1M": 2.0, "output_cost_per_1M": 12.0})
    return cfg


def build_run_list(output: Path) -> int:
    with SELECTION_MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))
    wanted = {row["sample_id"] for row in manifest_rows}
    group_counts: dict[str, int] = {}
    for row in manifest_rows:
        label = row["selection_group"]
        group_counts[label] = group_counts.get(label, 0) + 1
    if len(wanted) != EXPECTED_SAMPLES or set(group_counts.values()) != {SAMPLES_PER_TYPE}:
        raise SystemExit(
            f"invalid selection manifest: expected {N_CLASSES} groups x {SAMPLES_PER_TYPE} "
            f"unique samples; found {len(wanted)} samples and counts {group_counts}"
        )
    catalog_path = REPO_ROOT / "data/real_human/metadata.jsonl"
    catalog = [json.loads(line) for line in catalog_path.read_text().splitlines() if line.strip()]
    selected = [row for row in catalog if row["sample_id"] in wanted]
    missing = wanted - {row["sample_id"] for row in selected}
    if missing:
        raise SystemExit(f"selected sample IDs missing from catalog: {sorted(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row) + "\n" for row in selected), encoding="utf-8")
    return len(selected)


def link_media_cache() -> None:
    """Reuse the design-choice media cache when present (identical condition)."""
    ours = RUNS_ROOT / ".media_cache"
    if not ours.exists() and DESIGN_CACHE.is_dir():
        RUNS_ROOT.mkdir(parents=True, exist_ok=True)
        ours.symlink_to(DESIGN_CACHE.resolve())
        print(f"media cache: reusing {DESIGN_CACHE}")


def require_complete(run_dir: Path, expected: int) -> None:
    predictions = run_dir / "predictions.jsonl"
    completed = runner.successful_sample_ids(predictions)
    if len(completed) != expected:
        raise SystemExit(
            f"incomplete run: {run_dir} has {len(completed)}/{expected} successful samples. "
            "Rerun the same command to retry only failures."
        )


def process_metrics(run_id: str) -> None:
    processed = RUNS_ROOT / "processed" / run_id
    result_dir = RUNS_ROOT / "results" / run_id
    subprocess.run([
        sys.executable, "scripts/data_processing/build_detection_table.py",
        "--runs-root", str(RUNS_ROOT), "--run-ids", run_id,
        "--outdir", str(processed),
    ], cwd=REPO_ROOT, check=True)
    subprocess.run([
        sys.executable, "scripts/results_rendering/report_stats.py",
        "--table", str(processed / "detections_long.csv"),
        "--by-task", "--outdir", str(result_dir),
    ], cwd=REPO_ROOT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", choices=sorted(MODEL_TRANSPORT), default=DEFAULT_MODEL,
                    help="gemini_3_flash = cheap screening (default); "
                         "gemini_3_1_pro = anchor-model confirmation")
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default=DEFAULT_PROVIDER,
                    help="API route/billing for VLM arms (default: arena, Carrie's key)")
    ap.add_argument("--arm", action="append", choices=sorted(ALL_ARMS),
                    help="run only this arm; repeatable (default depends on --model)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None,
                    help="run only the first N selected samples (for validation)")
    ap.add_argument("--run-prefix", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    model = args.model
    prefix = args.run_prefix or f"promptabl2_{model}"
    if args.arm:
        arms = args.arm
    elif model == "gemini_3_1_pro":
        # Anchor model: the committed design-choice baseline is the B arm.
        arms = [a for a in ALL_ARMS if not a.endswith("_b")]
    else:
        # Screening model: no committed baseline exists, so run B arms too.
        arms = list(ALL_ARMS)
    expected = args.limit or EXPECTED_SAMPLES
    est = MODEL_TRANSPORT[model]["est_cost_per_arm"]
    n_vlm = sum(1 for a in arms if a in VLM_ARMS)

    print(f"vlm={model} provider={args.provider} parser={PARSER_MODEL} "
          f"condition={json.dumps(CONDITION)} samples={expected}")
    print(f"estimated VLM cost: {n_vlm} arm(s) x ~${est} = ~${n_vlm * est} "
          f"(80-clip basis; scale down for --limit)")
    if model == "gemini_3_1_pro":
        print(f"B arm for comparison: committed run {BASELINE_RUN} (OpenRouter). "
              "Note: a different --provider for variant arms adds a route confound.")
    for arm in arms:
        spec = ALL_ARMS[arm]
        kind = "parser-only" if arm in PARSER_ARMS else "VLM"
        vp = variant_path(arm)
        src = vp.relative_to(REPO_ROOT) if vp else "prompts/ (committed baseline)"
        print(f"{prefix}_{arm}: {spec['task']} cand={spec['cand'] or 'B'} [{kind}] prompt={src}")
        if vp and not vp.is_file():
            raise SystemExit(f"missing variant prompt: {vp}")
    if any(a in PARSER_ARMS for a in arms) and not BASELINE_P3_DIR.is_dir():
        raise SystemExit(f"baseline P3 output not found: {BASELINE_P3_DIR}")
    if args.dry_run:
        return

    if args.provider == "arena" and not os.environ.get("ARENA_API_KEY"):
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not token:
            raise SystemExit("arena provider needs ARENA_API_KEY or ANTHROPIC_AUTH_TOKEN set")
        os.environ["ARENA_API_KEY"] = token

    run_list = RUNS_ROOT / "run_lists" / f"{prefix}_selected_{EXPECTED_SAMPLES}.jsonl"
    count = build_run_list(run_list)
    if count != EXPECTED_SAMPLES:
        raise SystemExit(f"expected {EXPECTED_SAMPLES} selected cases, found {count}")
    link_media_cache()
    base = runner.load_config()
    cfg = build_cfg(base, model, args.provider)

    if args.limit:
        skipped = [a for a in arms if a in PARSER_ARMS]
        if skipped:
            # run_parser has no limit support; it would parse all 80 baseline
            # rows and then fail the completeness check against --limit.
            print(f"--limit set: skipping parser arm(s) {skipped} (run them in the full run)")
            arms = [a for a in arms if a not in PARSER_ARMS]

    completed_run_ids = []
    for arm in arms:
        spec = ALL_ARMS[arm]
        run_id = f"{prefix}_{arm}"
        if spec["cand"] is not None:
            set_active(spec["ptype"], spec["cand"])
        try:
            if arm in VLM_ARMS:
                run_dir = runner.collect(
                    spec["task"], model, cfg, run_id=run_id,
                    data_list=run_list, camera_views=CONDITION["views"],
                    limit=args.limit, concurrency=args.concurrency,
                    runs_root=RUNS_ROOT, data_root=REPO_ROOT / "data",
                )
            else:
                parser_cfg = copy.deepcopy(cfg)
                parser_cfg["defaults"]["call"]["max_completion_tokens"] = 2048
                run_dir = runner.run_parser(
                    spec["task"], PARSER_MODEL, BASELINE_P3_DIR, parser_cfg,
                    run_id=run_id, concurrency=args.concurrency, runs_root=RUNS_ROOT,
                )
        finally:
            ACTIVE.pop(spec["ptype"], None)
        require_complete(run_dir, expected)
        if args.limit:
            # Validation mode: the detection table emits one row per failure
            # subtype, and a tiny subset (often all-success clips) can be empty,
            # which crashes the stats step. Raw predictions are the deliverable.
            print(f"--limit set: skipping processed metrics for {run_id}; "
                  f"inspect {run_dir}/predictions.jsonl")
        else:
            process_metrics(run_id)
        completed_run_ids.append(run_id)

    if args.limit:
        print("validation complete; raw predictions per arm are under runs/raw/")
        return
    cost_cmd = [
        sys.executable, "scripts/results_rendering/summarize_cost.py",
        "--runs-root", str(RUNS_ROOT),
        "--outdir", str(RUNS_ROOT / "results" / f"{prefix}_costs"),
    ]
    for run_id in completed_run_ids:
        cost_cmd.extend(["--run-id", run_id])
    subprocess.run(cost_cmd, cwd=REPO_ROOT, check=True)
    print(f"raw: {RUNS_ROOT / 'raw'}")
    print(f"results: {RUNS_ROOT / 'results'}")
    print(f"Compare against the committed B arm: "
          f"../eval_design_choices/results/{BASELINE_RUN}/")


if __name__ == "__main__":
    main()
