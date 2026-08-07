#!/usr/bin/env python3
"""Prompt-ablation driver. Redirects prompt loading to variant files (no change to
committed prompts/ or src/) and runs every candidate x model into
design_justification/prompt_design_choice/pilot_n10_contact_sheets/runs/ (media cache gitignored).

Phases:
  1. VLM collect for P1,P2,P3,P4 x {B,V1,V2} x models  -> run_id p{n}__{cand}
  2. Parser passes:
       - P3 scoring: parse each p3__{cand} VLM output with BASELINE p5 -> run_id p3__{cand}
       - P4 scoring: parse each p4__{cand} VLM output with BASELINE p6 -> run_id p4__{cand}
       - P5 ablation: parse the p3__B VLM output with p5 {B,V1,V2}    -> run_id p5__{cand}
       - P6 ablation: parse the p4__B VLM output with p6 {B,V1,V2}    -> run_id p6__{cand}
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from labos_benchmark import runner
from labos_benchmark import prompts as P  # noqa: E402

MODELS = ["qwen3_vl", "claude_opus_4_8", "gemini_3_1_pro"]
PARSER_LLM = "gpt_5_5_parser"
CANDS = ["B", "V1", "V2"]
CAMS = ["front", "gripper"]
DATA = str(HERE / "run_list_10.jsonl")
RUNS_ROOT = str(HERE / "runs")
VARIANTS = HERE / "variants"
CONC = 8

FILES = {
    "closed_binary": "p1_closed_binary.md",
    "multilabel_classification": "p2_multilabel_classification.md",
    "open_detection_strict": "p3_open_detection_strict.md",
    "open_detection_free": "p4_open_detection_free.md",
    "open_detection_strict_parser": "p5_open_detection_strict_parser.md",
    "open_detection_free_parser": "p6_open_detection_free_parser.md",
}

# ---- prompt-loading redirection ------------------------------------------- #
ACTIVE: dict[str, str] = {}  # ptype -> variant file path


def _patched_get_prompt_path(task_name, prompts_dir=None):
    ptype = P.prompt_type_of(task_name)
    if ptype in ACTIVE:
        return Path(ACTIVE[ptype])
    return P.PROMPTS_DIR / FILES[ptype]  # baseline fallback


P.get_prompt_path = _patched_get_prompt_path  # module global used by load_prompt & runner


def set_active(ptype: str, cand: str) -> None:
    ACTIVE[ptype] = str(VARIANTS / ptype / cand / FILES[ptype])


VLM_PROMPTS = [
    ("closed_binary", "vortex_closed_binary", "p1"),
    ("multilabel_classification", "vortex_multilabel_classification", "p2"),
    ("open_detection_strict", "vortex_open_detection_strict", "p3"),
    ("open_detection_free", "vortex_open_detection_free", "p4"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma list of phases: vlm,p3parse,p4parse,p5,p6")
    args = ap.parse_args()
    phases = set((args.only or "vlm,p3parse,p4parse,p5,p6").split(","))

    cfg = runner.load_config()
    vlm_dirs: dict[tuple, Path] = {}  # (tag, cand, model) -> vlm run dir

    # ---- Phase 1: VLM collect ------------------------------------------- #
    if "vlm" in phases:
        for ptype, task, tag in VLM_PROMPTS:
            for cand in CANDS:
                set_active(ptype, cand)
                run_id = f"{tag}__{cand}"
                for model in MODELS:
                    print(f"[VLM] {run_id} :: {model}", flush=True)
                    rd = runner.collect(task, model, cfg, run_id=run_id, data_list=DATA,
                                        camera_views=CAMS, concurrency=CONC,
                                        runs_root=RUNS_ROOT)
                    vlm_dirs[(tag, cand, model)] = rd

    def vlm_dir(tag, cand, model):
        rd = vlm_dirs.get((tag, cand, model))
        if rd is None:  # recover path if phase 1 skipped this session
            rd = Path(RUNS_ROOT) / "raw" / f"{tag}__{cand}" / \
                {"p3": "vortex_open_detection_strict", "p4": "vortex_open_detection_free"}[tag] / model
        return rd

    # ---- Phase 2a: P3 scoring (baseline p5 over each p3 candidate) ------- #
    if "p3parse" in phases:
        set_active("open_detection_strict_parser", "B")
        for cand in CANDS:
            for model in MODELS:
                src = vlm_dir("p3", cand, model)
                print(f"[P3->p5B] p3__{cand} :: {model}", flush=True)
                runner.run_parser("vortex_open_detection_strict_parser", PARSER_LLM, src, cfg,
                                  run_id=f"p3__{cand}", concurrency=CONC, runs_root=RUNS_ROOT)

    # ---- Phase 2b: P4 scoring (baseline p6 over each p4 candidate) ------- #
    if "p4parse" in phases:
        set_active("open_detection_free_parser", "B")
        for cand in CANDS:
            for model in MODELS:
                src = vlm_dir("p4", cand, model)
                print(f"[P4->p6B] p4__{cand} :: {model}", flush=True)
                runner.run_parser("vortex_open_detection_free_parser", PARSER_LLM, src, cfg,
                                  run_id=f"p4__{cand}", concurrency=CONC, runs_root=RUNS_ROOT)

    # ---- Phase 2c: P5 ablation (p5 candidates over p3__B VLM output) ----- #
    if "p5" in phases:
        for cand in CANDS:
            set_active("open_detection_strict_parser", cand)
            for model in MODELS:
                src = vlm_dir("p3", "B", model)
                print(f"[P5abl] p5__{cand} :: {model}", flush=True)
                runner.run_parser("vortex_open_detection_strict_parser", PARSER_LLM, src, cfg,
                                  run_id=f"p5__{cand}", concurrency=CONC, runs_root=RUNS_ROOT)

    # ---- Phase 2d: P6 ablation (p6 candidates over p4__B VLM output) ----- #
    if "p6" in phases:
        for cand in CANDS:
            set_active("open_detection_free_parser", cand)
            for model in MODELS:
                src = vlm_dir("p4", "B", model)
                print(f"[P6abl] p6__{cand} :: {model}", flush=True)
                runner.run_parser("vortex_open_detection_free_parser", PARSER_LLM, src, cfg,
                                  run_id=f"p6__{cand}", concurrency=CONC, runs_root=RUNS_ROOT)

    print("=== ABLATION COLLECTION DONE ===", flush=True)


if __name__ == "__main__":
    main()
