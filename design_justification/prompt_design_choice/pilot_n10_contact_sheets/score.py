#!/usr/bin/env python3
"""Score the prompt ablation directly from raw prediction records (NOT the
detection table, which silently drops `ambiguous` rows and would reward a parser
for dodging via `ambiguous`). For each candidate we read every prediction's
`expected` (ground truth) and `prediction` (model output) and compute:

  outcome metrics on one record per clip, with `ambiguous` counted as a MISS:
    success_recall  = P(pred==success | truth==success)
    failure_recall  = P(pred==failure | truth==failure)
    balanced_accuracy = mean(success_recall, failure_recall)
  subtype metrics (P2/P3/P4/P5/P6, which emit failure_modes):
    macro_f1_subtype = mean over the 7 canonical subtypes of F1(expected vs predicted mode)

Winner per prompt = max mean balanced accuracy across models; macro-F1 tie-break;
prefer B on an exact tie (no wording change without a real gain).
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "raw"
OUT = HERE / "results"

MODELS = ["qwen3_vl", "claude_opus_4_8", "gemini_3_1_pro"]
CANDS = ["B", "V1", "V2"]
SUBTYPES = ["cap_open", "tube_drop", "tube_empty", "vortex_off",
            "wrong_orientation", "wrong_rack", "rack_flipped"]

# prompt -> (run_id task subdir, is_parser)
TASKDIR = {
    "p1": ("vortex_closed_binary", False),
    "p2": ("vortex_multilabel_classification", False),
    "p3": ("vortex_open_detection_strict_parser", True),
    "p4": ("vortex_open_detection_free_parser", True),
    "p5": ("vortex_open_detection_strict_parser", True),
    "p6": ("vortex_open_detection_free_parser", True),
}
HAS_SUBTYPES = {"p1": False, "p2": True, "p3": True, "p4": True, "p5": True, "p6": True}


def run_id_norm(prompt: str, cand: str) -> str:
    return f"{prompt}_{cand}".lower()   # matches safe_name lowering of p{n}__{cand}


def load_preds(prompt: str, cand: str, model: str):
    taskdir, is_parser = TASKDIR[prompt]
    base = RUNS / run_id_norm(prompt, cand) / taskdir / model
    files = list(base.glob("*/predictions.jsonl")) if is_parser else [base / "predictions.jsonl"]
    recs = []
    for f in files:
        if f.exists():
            recs += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return recs


def _f1(tp, fp, fn):
    if tp == 0:
        return 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0


def score(recs, want_subtypes):
    by_sample = {}
    for r in recs:
        exp = r.get("expected") or {}
        pred = r.get("prediction") or {}
        by_sample[r.get("sample_id")] = (
            exp.get("outcome"), pred.get("outcome") if r.get("success") else None,
            set(exp.get("failure_modes") or []), set(pred.get("failure_modes") or []),
        )
    succ = [v for v in by_sample.values() if v[0] == "success"]
    fail = [v for v in by_sample.values() if v[0] == "failure"]
    srec = sum(1 for v in succ if v[1] == "success") / len(succ) if succ else float("nan")
    frec = sum(1 for v in fail if v[1] == "failure") / len(fail) if fail else float("nan")
    vals = [x for x in (srec, frec) if x == x]
    bal = sum(vals) / len(vals) if vals else float("nan")
    n_amb = sum(1 for v in by_sample.values() if v[1] == "ambiguous")
    n_bad = sum(1 for v in by_sample.values() if v[1] not in ("success", "failure", "ambiguous"))
    macro = float("nan")
    if want_subtypes:
        f1s = []
        for s in SUBTYPES:
            tp = fp = fn = 0
            for _o, _p, tset, pset in by_sample.values():
                t, p = s in tset, s in pset
                tp += t and p; fp += p and not t; fn += t and not p
            f1s.append(_f1(tp, fp, fn))
        macro = sum(f1s) / len(f1s) if f1s else float("nan")
    return dict(n=len(by_sample), success_recall=srec, failure_recall=frec,
                balanced_accuracy=bal, macro_f1_subtype=macro,
                n_ambiguous=n_amb, n_failed=n_bad)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    per_rows, agg = [], {}
    for prompt in ["p1", "p2", "p3", "p4", "p5", "p6"]:
        for cand in CANDS:
            bals, macros, amb = [], [], 0
            for model in MODELS:
                recs = load_preds(prompt, cand, model)
                if not recs:
                    continue
                m = score(recs, HAS_SUBTYPES[prompt])
                per_rows.append(dict(prompt=prompt, cand=cand, model=model, **m))
                if m["balanced_accuracy"] == m["balanced_accuracy"]:
                    bals.append(m["balanced_accuracy"])
                if m["macro_f1_subtype"] == m["macro_f1_subtype"]:
                    macros.append(m["macro_f1_subtype"])
                amb += m["n_ambiguous"]
            if bals:
                agg[(prompt, cand)] = dict(
                    mean_balanced=sum(bals) / len(bals),
                    mean_macro_f1=(sum(macros) / len(macros)) if macros else float("nan"),
                    total_ambiguous=amb, n_models=len(bals))

    with open(OUT / "per_model_metrics.csv", "w") as f:
        f.write("prompt,cand,model,n,success_recall,failure_recall,balanced_accuracy,"
                "macro_f1_subtype,n_ambiguous,n_failed\n")
        for r in per_rows:
            f.write(f"{r['prompt']},{r['cand']},{r['model']},{r['n']},"
                    f"{r['success_recall']:.3f},{r['failure_recall']:.3f},"
                    f"{r['balanced_accuracy']:.3f},{r['macro_f1_subtype']:.3f},"
                    f"{r['n_ambiguous']},{r['n_failed']}\n")

    lines = ["# Prompt-ablation results (scored from raw predictions; `ambiguous` = miss)\n",
             "Mean balanced accuracy across qwen3_vl / claude_opus_4_8 / gemini_3_1_pro,",
             "10 clips (3 success + 7 single-mode failures). macro-F1 over 7 subtypes (P2-P6).\n"]
    winners = {}
    for prompt in ["p1", "p2", "p3", "p4", "p5", "p6"]:
        cs = [(c, agg[(prompt, c)]) for c in CANDS if (prompt, c) in agg]
        if not cs:
            continue
        def key(x):
            c, s = x
            mf = s["mean_macro_f1"] if s["mean_macro_f1"] == s["mean_macro_f1"] else -1
            return (round(s["mean_balanced"], 6), round(mf, 6), 1 if c == "B" else 0)
        win = sorted(cs, key=key, reverse=True)[0][0]
        winners[prompt] = win
        lines.append(f"\n## {prompt.upper()} → winner: **{win}**")
        lines.append("| cand | mean_balanced | mean_macro_f1 | ambig |")
        lines.append("|---|---|---|---|")
        for c, s in cs:
            star = " ⭐" if c == win else ""
            lines.append(f"| {c}{star} | {s['mean_balanced']:.3f} | {s['mean_macro_f1']:.3f} | {s['total_ambiguous']} |")
    lines.append("\n## Winners\n| prompt | winner |\n|---|---|")
    for p in ["p1", "p2", "p3", "p4", "p5", "p6"]:
        if p in winners:
            lines.append(f"| {p} | {winners[p]} |")
    report = "\n".join(lines) + "\n"
    (OUT / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
