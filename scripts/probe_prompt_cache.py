#!/usr/bin/env python3
"""Probe whether a provider route serves our shared media prefix from cache.

Sends three calls for ONE clip, back-to-back, mimicking what collect_suite()
does per clip:

  call 1: task A               — cold; should write the provider-side cache
  call 2: task B               — same media prefix, different trailing prompt
                                 text AND different response_format schema
  call 3: task A again         — byte-identical payload to call 1

then prints each call's usage (prompt/cached tokens, cost, provider). Reading:

  * call 3 cached>0 but call 2 cached==0  -> caching works on this route, but
    the per-task prompt tail / response_format breaks the prefix; suite mode
    saves little until that is fixed.
  * call 2 cached>0                       -> clip-grouped suite runs bill the
    media prefix at the cached rate; scale projection is in
    docs/MODEL_ROSTER_AND_BUDGET.md §4.
  * call 3 cached==0                      -> no implicit caching observed on
    this route (check provider pinning, or try google-vertex / direct API).

Cost: one clip x 3 calls (~$5 at the full 128x3-frame design on Gemini list
price; use --camera-views front to probe at ~1/3 that). Requires a route
pinned to a single provider, e.g. gemini_3_1_pro_or in config/models.yaml.

Without the video data on disk, --synthetic-frames N builds a stand-in payload
(N tiny JPEGs x --synthetic-views, same label structure as the real frames
pipeline). Gemini bills small images at a fixed ~258 tokens each, so 128x3
synthetic frames still exercise a ~100k-token prefix — enough to answer the
caching question at ~1/25 the token cost of a real clip.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labos_benchmark import client, prompts, runner, schemas  # noqa: E402
from labos_benchmark.adapters import get_adapter  # noqa: E402
from labos_benchmark.dataset import load_datapoints  # noqa: E402

# Smallest valid JPEG (1x1 px, gray) — payload stand-in when no videos exist locally.
_TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)


def synthetic_media(frames_per_view: int, views: list[str]) -> list[dict]:
    """Frame blocks shaped exactly like media.maybe_transcode_videos (frames mode)."""
    out_dir = Path(tempfile.mkdtemp(prefix="probe_cache_"))
    frame = out_dir / "frame.jpg"
    frame.write_bytes(_TINY_JPEG)
    intro = (
        f"The following images are grouped into {len(views)} synchronized camera "
        f"views in this order: {', '.join(views)}. Within each view, frames are "
        "uniformly sampled across the full execution and ordered chronologically."
    )
    media: list[dict] = []
    for view in views:
        for index in range(1, frames_per_view + 1):
            label = None
            if index == 1:
                label = f"[{view.upper()} VIEW — {frames_per_view} frames]"
                if not media:
                    label = f"{intro}\n\n{label}"
            media.append({"type": "image", "path": str(frame),
                          **({"label": label} if label else {})})
    return media


def _cached_tokens(usage: dict) -> int:
    """Best-effort cached-token count across provider usage formats."""
    details = usage.get("prompt_tokens_details") or {}
    for source in (details, usage):
        for key in ("cached_tokens", "cache_read_input_tokens", "cached_input_tokens"):
            if source.get(key) is not None:
                return int(source[key])
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="gemini_3_1_pro_or",
                    help="model name from config/models.yaml (default: %(default)s)")
    ap.add_argument("--data", default=None, help="run_list.jsonl under data/")
    ap.add_argument("--synthetic-frames", type=int, default=None, metavar="N",
                    help="probe without local videos: N tiny JPEG frames per view")
    ap.add_argument("--synthetic-views", type=int, default=3,
                    help="number of synthetic views (default: %(default)s)")
    ap.add_argument("--operation", default="vortex")
    ap.add_argument("--tasks", nargs=2, default=["closed_binary", "multilabel_classification"],
                    metavar=("TASK_A", "TASK_B"),
                    help="two VLM prompt types; task = {operation}_{prompt_type}")
    ap.add_argument("--sample-index", type=int, default=0,
                    help="which datapoint from --data to probe with")
    ap.add_argument("--camera-views", nargs="*", default=None,
                    help="subset of angles (default: configured views)")
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args()
    if (args.data is None) == (args.synthetic_frames is None):
        ap.error("exactly one of --data / --synthetic-frames is required")

    # Arena convention (design_choices runner): ARENA_API_KEY falls back to the token.
    if not os.environ.get("ARENA_API_KEY") and os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        os.environ["ARENA_API_KEY"] = os.environ["ANTHROPIC_AUTH_TOKEN"]

    cfg = runner.load_config()
    defaults = cfg["defaults"]
    media_cfg = defaults.get("media", {})
    call_cfg = defaults.get("call", {})
    model_cfg = runner._model_cfg_with_call_defaults(cfg["models"][args.model], call_cfg)
    adapter = get_adapter(model_cfg["adapter"], model_cfg)
    cams = args.camera_views if args.camera_views is not None else media_cfg.get("camera_views", [])
    max_videos = int(media_cfg.get("max_videos_per_sample", 0) or 0)

    if args.synthetic_frames is not None:
        views = (cams or ["front", "left", "right"])[: args.synthetic_views]
        media = synthetic_media(args.synthetic_frames, views)
        sample_id = "synthetic_probe"
    else:
        points = load_datapoints(args.data)
        dp = points[args.sample_index]
        sample_id = dp.sample_id
        media = runner.prepare_clip_media(dp, media_cfg=media_cfg, cams=cams,
                                          max_videos=max_videos,
                                          runs_root=args.runs_root, data_root=args.data_root)
    print(f"probing model={args.model} clip={sample_id} "
          f"media_blocks={len(media)}", flush=True)

    task_a, task_b = (f"{args.operation}_{p}" for p in args.tasks)
    sequence = [
        (f"{task_a} (cold)", task_a),
        (f"{task_b} (shared media prefix)", task_b),
        (f"{task_a} (identical repeat)", task_a),
    ]
    rows = []
    for i, (label, task) in enumerate(sequence, start=1):
        if i > 1:
            time.sleep(2)  # give the provider a moment to persist the cache entry
        result, ar = client.call_with_retries(
            adapter,
            prompt=prompts.load_prompt(task),
            media=media,
            request_metadata={"probe": "prompt_cache", "task": task, "sample_id": sample_id},
            model_name=args.model,
            cost_entry=cfg["model_costs"].get(model_cfg.get("provider_model_id")),
            max_retries=2,
            parse_fn=None,
            response_format=schemas.response_format_for_task(task),
        )
        usage = (ar.usage or {}) if ar is not None else {}
        provider = (ar.provider_response or {}).get("provider") if ar is not None else None
        row = {
            "call": i, "label": label,
            "prompt_tokens": usage.get("prompt_tokens"),
            "cached_tokens": _cached_tokens(usage),
            "completion_tokens": usage.get("completion_tokens"),
            "cost": usage.get("cost"),
            "provider": provider,
            "success": result.success,
        }
        rows.append(row)
        print(f"\n--- call {i}: {label} ---")
        print(f"success={result.success} provider={provider} "
              f"latency={ar.latency_s:.1f}s" if ar is not None else "no response")
        print(f"usage: {json.dumps(usage, indent=2, default=str)}")

    print("\n=== summary ===")
    for row in rows:
        print(f"call {row['call']}: prompt={row['prompt_tokens']} cached={row['cached_tokens']} "
              f"cost={row['cost']} ({row['label']})")

    c1, c2, c3 = rows
    if not all(r["success"] for r in rows):
        print("VERDICT: inconclusive — at least one call failed; fix that before reading cache numbers.")
    elif c2["cached_tokens"] > 0:
        print("VERDICT: PASS — cross-task cache hit. Clip-grouped suite runs "
              "(scripts/data_collection/run_vlm_suite.py) will bill the media prefix "
              "at the cached rate.")
    elif c3["cached_tokens"] > 0:
        print("VERDICT: PARTIAL — identical repeats hit the cache but the per-task "
              "prompt tail / response_format breaks the shared prefix. Suite mode "
              "won't save much as-is.")
    else:
        print("VERDICT: FAIL — no cached tokens observed on this route. Check provider "
              "pinning (extra_body.provider in config/models.yaml), try google-vertex, "
              "or probe the direct Gemini API instead.")
    if c1["cost"] and c2["cost"]:
        print(f"call 2 cost is {c2['cost'] / c1['cost']:.0%} of call 1 "
              f"(3-prompt suite input would scale by ~{(1 + 2 * c2['cost'] / c1['cost']) / 3:.2f}x).")


if __name__ == "__main__":
    main()
