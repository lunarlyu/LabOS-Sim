"""Summarize binary benchmark runs into a markdown tracking file."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def money(value: float) -> str:
    return f"${value:.6f}"


def summarize_run(
    root: Path,
    label: str,
    run_dir: Path,
    display_run_dir: str,
    config_path: Path,
    samples_by_id: dict,
) -> dict:
    predictions_path = run_dir / "predictions.jsonl"
    rows = [
        json.loads(line)
        for line in predictions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    config = load_json(config_path)

    totals = Counter()
    resolved_models: Counter[str] = Counter()
    per_sample = []

    for row in rows:
        response_path = root / row["response_artifact"]
        response = load_json(response_path)
        usage = response.get("usage") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        completion_details = usage.get("completion_tokens_details") or {}

        totals["cost"] += float(usage.get("cost") or 0)
        totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["reasoning_tokens"] += int(completion_details.get("reasoning_tokens") or 0)
        totals["video_tokens"] += int(prompt_details.get("video_tokens") or 0)
        resolved_models[response.get("model") or row["model"]] += 1

        expected = bool(row["expected"]["success"])
        prediction = None if row.get("prediction") is None else bool(row["prediction"].get("success"))
        correct = prediction == expected
        if correct:
            totals["correct"] += 1
        if expected and prediction is True:
            totals["tp"] += 1
        elif (not expected) and prediction is False:
            totals["tn"] += 1
        elif (not expected) and prediction is True:
            totals["fp"] += 1
        elif expected and prediction is False:
            totals["fn"] += 1
        if row.get("parse_error"):
            totals["parse_errors"] += 1

        sample = samples_by_id[row["sample_id"]]
        label_tags = sample.get("scenario_tags") if expected else sample.get("failure_modes")
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "path": row["sample_path"],
                "label": ",".join(label_tags or []),
                "videos": len(sample.get("videos") or []),
                "expected": "success" if expected else "failure",
                "prediction": (
                    "parse_error"
                    if prediction is None
                    else ("success" if prediction else "failure")
                ),
                "correct": correct,
                "confidence": "" if not row.get("prediction") else row["prediction"].get("confidence", ""),
                "observed_failure": ""
                if not row.get("prediction")
                else row["prediction"].get("observed_failure", ""),
                "cost": float(usage.get("cost") or 0),
            }
        )

    totals["total"] = len(rows)
    return {
        "label": label,
        "run_dir": display_run_dir,
        "config_path": config_path,
        "config": config,
        "resolved_models": dict(resolved_models),
        "totals": totals,
        "per_sample": per_sample,
    }


def render_markdown(summaries: list[dict]) -> str:
    first_samples = summaries[0]["per_sample"]
    lines = [
        "# LabOS-Sim Baseline Tracking",
        "",
        "Updated: 2026-06-12",
        "",
        "## Baseline: Binary Success Detection, 10 Samples",
        "",
        "Purpose: first reproducible binary benchmark over 3 clean successes and 7 failure cases using OpenRouter video calls. The prompt asks whether the vortexing task succeeded under the current success criteria, and the model must return parseable JSON only.",
        "",
        "### Fixed Configuration",
        "",
        "| Setting | Value |",
        "|---|---|",
        "| Task | `binary_success` only |",
        "| Dataset metadata | `metadata/real_human_samples.json` |",
        "| Sample panel | 3 `clean` successes + 7 failures, one from each major failure folder |",
        "| Video views | all available camera views per sample |",
        "| Videos per sample | all videos, normally 5 |",
        "| Media profile | `canonical_clip_720px_15fps` |",
        "| Preprocess | transcode to max width 720px, 15fps, CRF 28, preset `veryfast` |",
        "| Temperature | 0 |",
        "| Structured output enforcement | disabled for video compatibility; local JSON parsing still required |",
        "",
        "### Model Configurations",
        "",
        "| Model family | Config | Requested model | Resolved model(s) | Reasoning setting | Max completion tokens |",
        "|---|---|---|---|---|---:|",
    ]
    for summary in summaries:
        config = summary["config"]
        resolved = "<br>".join(f"`{model}`" for model in summary["resolved_models"])
        reasoning = json.dumps(config["openrouter"].get("reasoning", {}), separators=(",", ":"))
        lines.append(
            f"| {summary['label']} | `{summary['config_path']}` | `{config['models'][0]}` | {resolved} | `{reasoning}` | {config['openrouter']['max_completion_tokens']} |"
        )

    lines += [
        "",
        "### Sample Panel",
        "",
        "| # | Sample ID | Expected | Label | Videos | Path |",
        "|---:|---|---|---|---:|---|",
    ]
    for index, sample in enumerate(first_samples, start=1):
        lines.append(
            f"| {index} | `{sample['sample_id']}` | {sample['expected']} | {sample['label']} | {sample['videos']} | `{sample['path']}` |"
        )

    lines += [
        "",
        "### Aggregate Results",
        "",
        "| Model | Run directory | Completed | Parse errors | Accuracy | TP | TN | FP | FN | OpenRouter spend | Prompt tokens | Completion tokens | Reasoning tokens | Reported video tokens |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        totals = summary["totals"]
        total = totals["total"]
        accuracy = 100 * totals["correct"] / total if total else 0
        lines.append(
            f"| {summary['label']} | `{summary['run_dir']}` | {total}/{total} | {totals['parse_errors']} | {accuracy:.1f}% | {totals['tp']} | {totals['tn']} | {totals['fp']} | {totals['fn']} | {money(totals['cost'])} | {totals['prompt_tokens']} | {totals['completion_tokens']} | {totals['reasoning_tokens']} | {totals['video_tokens']} |"
        )

    lines += [
        "",
        "Notes: Gemini still consumes internal reasoning tokens even with `reasoning.exclude=true`; the reasoning text is not returned. MiniMax resolved to the dated endpoint shown above and reported `reasoning_tokens=0`. MiniMax does not report explicit `video_tokens` here; the video input appears in the much larger prompt-token count/cost instead.",
        "",
    ]

    for summary in summaries:
        lines += [
            f"### {summary['label']} Per-Sample Results",
            "",
            "| Sample | Expected | Prediction | Correct | Confidence | Observed failure | Cost |",
            "|---|---|---|---:|---:|---|---:|",
        ]
        for sample in summary["per_sample"]:
            observed = str(sample["observed_failure"]).replace("|", "/")
            lines.append(
                f"| `{sample['sample_id']}` | {sample['expected']} | {sample['prediction']} | {'yes' if sample['correct'] else 'no'} | {sample['confidence']} | {observed} | {money(sample['cost'])} |"
            )
        lines.append("")

    if len(summaries) >= 2:
        ranked = sorted(
            summaries,
            key=lambda item: item["totals"]["correct"] / item["totals"]["total"],
            reverse=True,
        )
        best = ranked[0]
        cheaper = min(summaries, key=lambda item: item["totals"]["cost"])
        best_acc = 100 * best["totals"]["correct"] / best["totals"]["total"]
        cheaper_acc = 100 * cheaper["totals"]["correct"] / cheaper["totals"]["total"]
        lines += ["### Initial Read", ""]
        if best["label"] == cheaper["label"]:
            lines.append(
                f"{best['label']} produced both the strongest and cheapest first binary baseline on this 10-sample panel: {best_acc:.1f}% accuracy for {money(best['totals']['cost'])} total OpenRouter spend."
            )
        else:
            lines.append(
                f"{best['label']} produced the stronger first binary baseline on this 10-sample panel at {best_acc:.1f}% accuracy for {money(best['totals']['cost'])} total OpenRouter spend. {cheaper['label']} was the cheaper run at {money(cheaper['totals']['cost'])} total spend, with {cheaper_acc:.1f}% accuracy on this panel."
            )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="benchmark_tracking.md")
    parser.add_argument(
        "--run",
        action="append",
        nargs=3,
        metavar=("LABEL", "RUN_DIR", "CONFIG"),
        required=True,
        help="Run summary triple. May be repeated.",
    )
    args = parser.parse_args()

    root = Path.cwd()
    metadata = load_json(root / "metadata/real_human_samples.json")
    samples_by_id = {sample["sample_id"]: sample for sample in metadata["samples"]}
    summaries = [
        summarize_run(root, label, root / run_dir, run_dir, Path(config), samples_by_id)
        for label, run_dir, config in args.run
    ]
    output = root / args.output
    output.write_text(render_markdown(summaries), encoding="utf-8")

    for summary in summaries:
        totals = summary["totals"]
        accuracy = totals["correct"] / totals["total"] if totals["total"] else 0
        print(
            f"{summary['label']}: accuracy={accuracy:.3f} "
            f"cost={totals['cost']:.6f} parse_errors={totals['parse_errors']}"
        )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
