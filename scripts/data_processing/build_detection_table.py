#!/usr/bin/env python3
"""Stage 1 of the SDT-IRT pipeline: raw labeling results -> tidy flag table.

This script turns the benchmark's raw predictions into a single clean, tidy
"long" table -- one row per ``(model, sample_id, subtype)`` cell -- that is both
(a) human-inspectable as a summary of the raw labeling results, and (b) the exact
input the SDT-IRT fitter (``fit_sdt_irt.py``) consumes. Stage 2 (the PyMC fit)
reads ``flags_long.csv`` and never touches the raw runs again.

It reads **either** task schema:

  * ``single_choice_multiclass``  -- the model picks exactly one ``choice``;
    the flagged subtype set is ``{choice}`` (empty for "success").
  * ``failure_mode_classification`` -- the model returns an importance-ordered
    ``failure_modes`` list. This benchmark has one ground-truth failure type per
    failure clip, so only the first (primary) predicted type is scored. Remaining
    returned types stay in raw predictions for diagnostics.

and either input form:

  * ``--csv per_sample_predictions.csv``  (a flat per-sample table; the
    single-choice reporter already emits one). Multi-label flat CSVs are
    supported too via a ``predicted_failure_modes`` column (``|``-separated).
  * ``--jsonl runs/<run>/predictions.jsonl --metadata data/<dataset>/metadata.jsonl``
    (the raw run + ground-truth metadata, for either schema).

Outputs (to --outdir):
  flags_long.csv            one row per (model, sample_id, subtype): is_present,
                            flagged, channel, confidence, outcomes, status
  per_model_summary.csv     per-model hits/misses/false-alarms, recall, FPR
  per_model_subtype.csv     same, split by subtype (the SDT cells)
  subtype_prevalence.csv    ground-truth positive counts per subtype
  table_summary.md          human-readable overview

Confidence note
---------------
``confidence`` is reported by the model for its *overall decision*, not per
subtype. We therefore attach the same decision-level confidence to every subtype
row of a given (model, sample) and mark it ``confidence_is_decision_level=True``.
It is carried through so a later graded-response / rating-ROC extension can use
it; the hard-flag M1/M2 fit ignores it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Canonical failure subtypes (mirrors prompts/PROMPT_CATALOG.md; repeated_steps removed).
DEFAULT_FAILURE_LABELS = [
    "cap_open",
    "tube_drop",
    "tube_empty",
    "vortex_off",
    "wrong_orientation",
    "wrong_rack",
    "rack_flipped",
    "other_failure",
]
SUCCESS_LABEL = "success"
AMBIGUOUS_LABEL = "ambiguous"  # p6 parser may return outcome="ambiguous"; held out of fitting


# --------------------------------------------------------------------------- #
# Per-(model, sample) records: a uniform intermediate the readers produce.
# Each record: dict(model, sample_id, truth_set, pred_set, confidence,
#                    outcome_truth, outcome_pred, status)
#   truth_set / pred_set : set[str] of failure subtypes (empty == success)
# --------------------------------------------------------------------------- #
def _truth_set_from_failure_modes(fm) -> set[str]:
    if not fm:
        return set()
    if isinstance(fm, str):
        fm = [x for x in fm.split("|") if x]
    return {str(x) for x in fm if x and str(x) != SUCCESS_LABEL}


def _ordered_failure_modes(fm) -> list[str]:
    """Normalize modes while preserving model-declared importance order."""
    if not fm:
        return []
    if isinstance(fm, str):
        fm = [x for x in fm.split("|") if x]
    return [str(x) for x in fm if x and str(x) != SUCCESS_LABEL]


def _primary_type(fm, outcome: str | None = None) -> str:
    """Single scored class: success or the first (most-important) failure mode."""
    modes = _ordered_failure_modes(fm)
    if modes:
        return modes[0]
    return SUCCESS_LABEL if outcome == SUCCESS_LABEL else "unclassified_failure"


def read_jsonl_run(jsonl: Path, metadata: Path) -> tuple[list[dict], str]:
    """Read a raw predictions.jsonl + ground-truth metadata -> records, schema."""
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    samples = meta["samples"] if isinstance(meta, dict) and "samples" in meta else meta
    truth_by_id = {
        s["sample_id"]: _truth_set_from_failure_modes(s.get("failure_modes"))
        for s in samples
    }
    truth_type_by_id = {
        s["sample_id"]: _primary_type(s.get("failure_modes"), s.get("outcome"))
        for s in samples
    }

    records: list[dict] = []
    schema = None
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pred = row.get("prediction") or {}
        status = row.get("status", "completed")
        # Detect schema from the first parsed prediction we see.
        if schema is None and pred:
            schema = "single_choice_multiclass" if "choice" in pred else "failure_mode_classification"

        if "choice" in pred:
            choice = pred.get("choice")
            pred_set = set() if choice in (None, SUCCESS_LABEL) else {choice}
        else:
            pred_set = _truth_set_from_failure_modes(pred.get("failure_modes"))

        sid = row["sample_id"]
        records.append({
            "model": row.get("model") or row.get("model_id"),
            "sample_id": sid,
            "truth_set": truth_by_id.get(sid, set()),
            "pred_set": pred_set,
            "truth_type": truth_type_by_id.get(sid, SUCCESS_LABEL),
            "pred_type": (
                choice if "choice" in pred and choice else
                _primary_type(pred.get("failure_modes"), pred.get("outcome"))
            ),
            "confidence": pred.get("confidence", None) if status == "completed" else None,
            "outcome_truth": "failure" if truth_by_id.get(sid) else "success",
            "outcome_pred": pred.get("outcome", None),
            "status": status,
        })
    return records, schema or "single_choice_multiclass"


def read_runs_root(runs_root: Path, metadata: Path | None = None,
                   include_run_ids: set[str] | None = None,
                   exclude_run_ids: set[str] | None = None) -> tuple[list[dict], str]:
    """Glob runs/raw/**/predictions.jsonl (the run_id-first layout) into records.

    Layout: runs/raw/{run_id}/{task}/{vlm}[/{llm}]/predictions.jsonl. Each record
    is the runner's row: {run_id, task, model, sample_id, prediction:{outcome,
    failure_modes, confidence,...}, success, expected:{outcome, failure_modes}}.
    Ground truth is read from each record's ``expected`` field (no metadata
    needed); ``--metadata`` is an optional fallback for older runs.

    ``include_run_ids`` (allowlist) and ``exclude_run_ids`` (denylist) filter by
    the leading run_id path segment, so e.g. smoke-test runs never contaminate a
    production table. include wins: if set, only those run_ids are read.
    """
    truth_by_id: dict[str, set] = {}
    if metadata is not None:
        meta = json.loads(Path(metadata).read_text(encoding="utf-8"))
        samples = meta["samples"] if isinstance(meta, dict) and "samples" in meta else meta
        truth_by_id = {s["sample_id"]: _truth_set_from_failure_modes(s.get("failure_modes"))
                       for s in samples}

    raw = Path(runs_root) / "raw"
    records: list[dict] = []
    for pj in sorted(raw.glob("**/predictions.jsonl")):
        rel = pj.relative_to(raw)               # {run_id}/{task}/{vlm}[/{llm}]/predictions.jsonl
        run_id = rel.parts[0]
        task = rel.parts[1] if len(rel.parts) > 1 else ""
        if include_run_ids is not None and run_id not in include_run_ids:
            continue
        if exclude_run_ids and run_id in exclude_run_ids:
            continue
        latest: dict[str, dict] = {}
        successful: dict[str, dict] = {}
        for line in pj.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            sid = row.get("sample_id")
            if not sid:
                continue
            latest[sid] = row
            if row.get("success") is True and row.get("prediction") is not None:
                successful[sid] = row
        # A resumed run appends retries. Score one row per sample, preferring the
        # latest successful response over any earlier transport/parse failures.
        rows = [successful.get(sid, row) for sid, row in latest.items()]
        for row in rows:
            pred = row.get("prediction") or {}
            # Skip raw freeform VLM outputs (open_detection_strict/free): they carry
            # observed_errors/description, not failure_modes, and must be ingested via
            # their parser run instead. Parse-error rows (prediction None) are kept
            # so they can be counted/dropped downstream.
            if row.get("success") and "failure_modes" not in pred:
                continue
            sid = row.get("sample_id")
            expected = row.get("expected") or {}
            if expected:
                truth_set = _truth_set_from_failure_modes(expected.get("failure_modes"))
                outcome_truth = expected.get("outcome") or ("failure" if truth_set else "success")
                truth_type = _primary_type(expected.get("failure_modes"), outcome_truth)
            else:                                # fallback to metadata
                truth_set = truth_by_id.get(sid, set())
                outcome_truth = "failure" if truth_set else "success"
                truth_type = next(iter(truth_set), SUCCESS_LABEL)
            scoring_model = row.get("source_vlm") if task.endswith("_parser") else row.get("model")
            records.append({
                "model": scoring_model or row.get("model"),
                "sample_id": sid,
                "truth_set": truth_set,
                "pred_set": _truth_set_from_failure_modes(pred.get("failure_modes")),
                "truth_type": truth_type,
                "pred_type": _primary_type(pred.get("failure_modes"), pred.get("outcome")),
                "confidence": pred.get("confidence"),
                "outcome_truth": outcome_truth,
                "outcome_pred": pred.get("outcome"),
                "status": "completed" if row.get("success") else "parse_error",
                "run_id": run_id,
                "task": task,
                "parser_llm": row.get("parser_llm") or (row.get("model") if task.endswith("_parser") else None),
            })
    return records, "failure_mode_classification"


def read_flat_csv(csv: Path) -> tuple[list[dict], str]:
    """Read a flat per_sample CSV (single-choice, or multi-label) -> records, schema."""
    df = pd.read_csv(csv)
    cols = set(df.columns)
    required = {"model", "sample_id", "expected_choice"}
    if not required <= cols:
        missing = sorted(required - cols)
        raise ValueError(f"flat CSV missing columns {missing}; have {sorted(cols)}")

    multilabel = "predicted_failure_modes" in cols
    schema = "failure_mode_classification" if multilabel else "single_choice_multiclass"

    df["expected_choice"] = df["expected_choice"].astype(str)
    if "status" in cols:
        df["status"] = df["status"].fillna("completed")
    else:
        df["status"] = "completed"

    records: list[dict] = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        truth_set = set() if d["expected_choice"] == SUCCESS_LABEL else {d["expected_choice"]}
        if multilabel:
            pred_set = _truth_set_from_failure_modes(d.get("predicted_failure_modes"))
        else:
            pc = str(d.get("predicted_choice") or "")
            pred_set = set() if pc in ("", SUCCESS_LABEL) else {pc}
        records.append({
            "model": d["model"],
            "sample_id": d["sample_id"],
            "truth_set": truth_set,
            "pred_set": pred_set,
            "truth_type": d["expected_choice"],
            "pred_type": (
                _primary_type(d.get("predicted_failure_modes"), d.get("outcome"))
                if multilabel else (pc or "unclassified_failure")
            ),
            "confidence": d.get("confidence", None),
            "outcome_truth": "failure" if truth_set else "success",
            "outcome_pred": d.get("outcome", None),
            "status": d.get("status", "completed"),
        })
    return records, schema


# --------------------------------------------------------------------------- #
# Records -> tidy long table + summaries
# --------------------------------------------------------------------------- #
def build_long_table(
    records: list[dict],
    drop_parse_errors: bool = True,
    drop_ambiguous: bool = True,
) -> pd.DataFrame:
    if drop_parse_errors:
        records = [r for r in records if r["status"] == "completed"]
    if drop_ambiguous:
        # p6 (parsed p2) may emit outcome="ambiguous"; those rows are unmappable
        # and are held out of the SDT-IRT fit rather than coerced to a flag.
        records = [r for r in records if r.get("outcome_pred") != AMBIGUOUS_LABEL]

    # Failure-type universe for SDT cells. Only the primary (first, most
    # important) predicted type is scored; extra model-returned types remain in
    # raw predictions for diagnostics but do not create additional flags.
    seen: set[str] = set()
    for r in records:
        seen |= {r.get("truth_type"), r.get("pred_type")}
    seen.discard(None)
    seen.discard(SUCCESS_LABEL)
    seen.discard("unclassified_failure")
    subtypes = [c for c in DEFAULT_FAILURE_LABELS if c in seen]
    subtypes += sorted(s for s in seen if s not in DEFAULT_FAILURE_LABELS)

    rows = []
    for r in records:
        for c in subtypes:
            is_present = int(c == r.get("truth_type"))
            rows.append({
                "run_id": r.get("run_id"),
                "task": r.get("task"),
                "model": r["model"],
                "sample_id": r["sample_id"],
                "subtype": c,
                "is_present": is_present,
                "flagged": int(c == r.get("pred_type")),
                "channel": "positive" if is_present else "negative",
                "confidence": r["confidence"],
                "confidence_is_decision_level": True,
                "outcome_truth": r["outcome_truth"],
                "outcome_pred": r["outcome_pred"],
                "truth_type": r.get("truth_type"),
                "pred_type": r.get("pred_type"),
                "status": r["status"],
                "parser_llm": r.get("parser_llm"),
            })
    return pd.DataFrame(rows)


def per_model_subtype_summary(long: pd.DataFrame) -> pd.DataFrame:
    g = long.groupby(["model", "subtype"], sort=False)
    out = g.apply(lambda d: pd.Series({
        "n_present": int(d["is_present"].sum()),
        "n_absent": int((1 - d["is_present"]).sum()),
        "hits": int(((d["is_present"] == 1) & (d["flagged"] == 1)).sum()),
        "false_alarms": int(((d["is_present"] == 0) & (d["flagged"] == 1)).sum()),
    }), include_groups=False).reset_index()
    out["recall"] = out.apply(lambda x: x["hits"] / x["n_present"] if x["n_present"] else float("nan"), axis=1)
    out["fpr"] = out.apply(lambda x: x["false_alarms"] / x["n_absent"] if x["n_absent"] else float("nan"), axis=1)
    return out


def per_model_summary(long: pd.DataFrame) -> pd.DataFrame:
    g = long.groupby("model", sort=False)
    out = g.apply(lambda d: pd.Series({
        "n_items": d["sample_id"].nunique(),
        "n_pos_cells": int(d["is_present"].sum()),
        "n_neg_cells": int((1 - d["is_present"]).sum()),
        "hits": int(((d["is_present"] == 1) & (d["flagged"] == 1)).sum()),
        "false_alarms": int(((d["is_present"] == 0) & (d["flagged"] == 1)).sum()),
        "mean_confidence": float(pd.to_numeric(d["confidence"], errors="coerce").mean()),
    }), include_groups=False).reset_index()
    out["recall"] = out["hits"] / out["n_pos_cells"]
    out["fpr"] = out["false_alarms"] / out["n_neg_cells"]
    return out


def subtype_prevalence(long: pd.DataFrame) -> pd.DataFrame:
    # is_present is model-invariant for a given (sample, subtype); dedupe to one
    # row per (sample, subtype) so a model that dropped a parse-error row does not
    # undercount the item denominator.
    one = long.drop_duplicates(subset=["sample_id", "subtype"])
    g = one.groupby("subtype", sort=False)["is_present"].agg(["sum", "count"]).reset_index()
    g.columns = ["subtype", "n_present", "n_items"]
    g["prevalence"] = g["n_present"] / g["n_items"]
    return g


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--runs-root", type=Path,
                     help="glob runs/raw/**/predictions.jsonl (the standard pipeline input)")
    src.add_argument("--csv", type=Path, help="flat per_sample_predictions.csv (legacy)")
    src.add_argument("--jsonl", type=Path, help="a single raw predictions.jsonl (legacy)")
    ap.add_argument("--metadata", type=Path,
                    help="optional ground-truth fallback json (truth normally comes "
                         "from each run record's 'expected' field; required with --jsonl)")
    ap.add_argument("--run-ids", nargs="+", default=None,
                    help="allowlist: only process these run_ids (the leading path segment "
                         "under runs/raw/). Use to select a production run and exclude smoke.")
    ap.add_argument("--exclude-run-ids", nargs="+", default=None,
                    help="denylist: skip these run_ids (e.g. 'smoke'). Ignored for run_ids "
                         "already selected by --run-ids.")
    ap.add_argument("--outdir", type=Path,
                    help="output dir (default: runs/processed for --runs-root)")
    ap.add_argument("--keep-parse-errors", action="store_true")
    ap.add_argument("--keep-ambiguous", action="store_true",
                    help="keep p6 outcome='ambiguous' rows (default: drop, held out of fitting)")
    args = ap.parse_args(argv)

    if args.runs_root:
        records, schema = read_runs_root(
            args.runs_root, args.metadata,
            include_run_ids=set(args.run_ids) if args.run_ids else None,
            exclude_run_ids=set(args.exclude_run_ids) if args.exclude_run_ids else None,
        )
        if args.outdir is None:
            args.outdir = Path("runs/processed")
    elif args.jsonl:
        if not args.metadata:
            ap.error("--metadata is required with --jsonl")
        records, schema = read_jsonl_run(args.jsonl, args.metadata)
    else:
        records, schema = read_flat_csv(args.csv)
    if args.outdir is None:
        ap.error("--outdir is required (no default for --csv/--jsonl)")

    n_total = len(records)
    n_parse_err = sum(1 for r in records if r["status"] != "completed")
    n_ambiguous = sum(1 for r in records if r.get("outcome_pred") == AMBIGUOUS_LABEL)

    long = build_long_table(
        records,
        drop_parse_errors=not args.keep_parse_errors,
        drop_ambiguous=not args.keep_ambiguous,
    )
    args.outdir.mkdir(parents=True, exist_ok=True)

    long.to_csv(args.outdir / "detections_long.csv", index=False)
    pm = per_model_summary(long)
    pms = per_model_subtype_summary(long)
    prev = subtype_prevalence(long)
    pm.to_csv(args.outdir / "per_model_summary.csv", index=False)
    pms.to_csv(args.outdir / "per_model_subtype.csv", index=False)
    prev.to_csv(args.outdir / "subtype_prevalence.csv", index=False)

    models = sorted(long["model"].unique())
    subtypes = list(prev["subtype"])
    lines = [
        "# Detection-table summary (Stage 1)\n",
        f"- Schema detected: **{schema}**",
        f"- Models (M={len(models)}): {', '.join(models)}",
        f"- Subtypes (C={len(subtypes)}): {', '.join(subtypes)}",
        f"- Items (I={long['sample_id'].nunique()}), detection cells (N={len(long)})",
        f"- Positive cells: {int(long['is_present'].sum())} | "
        f"negative cells: {int((1 - long['is_present']).sum())}",
        f"- Per-(model,sample) records: {n_total} total; "
        f"dropped {n_parse_err} parse-error and {n_ambiguous} ambiguous "
        f"(kept: {'yes' if args.keep_ambiguous else 'no'} ambiguous, "
        f"{'yes' if args.keep_parse_errors else 'no'} parse-error)\n",
        "## Ground-truth prevalence per subtype\n",
        prev.to_markdown(index=False),
        "",
        "## Per-model recall / FPR (hard 0.5 flag)\n",
        pm[["model", "n_items", "hits", "false_alarms", "recall", "fpr", "mean_confidence"]].to_markdown(index=False),
        "",
        "Feed `detections_long.csv` to `fit_sdt_irt.py` (Stage 2). Columns",
        "`is_present` (ground truth) and `flagged` (model said present) are the SDT",
        "positive/negative channels; `confidence` is decision-level, carried for a",
        "future graded-response extension.",
    ]
    (args.outdir / "table_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[schema] {schema}")
    print(f"[data] M={len(models)} C={len(subtypes)} I={long['sample_id'].nunique()} cells={len(long)}")
    print(f"[done] wrote tables to {args.outdir}")


if __name__ == "__main__":
    sys.exit(main())
