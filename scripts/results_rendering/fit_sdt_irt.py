#!/usr/bin/env python3
"""Fit the hierarchical SDT-IRT models M1 and M2 to LabOS vortexing predictions.

Background
----------
This implements models M1 and M2 from the design note
"Signal-Detection IRT for AI Evaluation on Success-vs-Multi-Failure Tasks"
(Lyu & Tan), applied to the data we currently collect for the vortexing
error-detection task.

Data we collect (``per_sample_predictions.csv``) is *single-choice*: each
(model, item) row carries one ground-truth label ``expected_choice`` and one
model label ``predicted_choice``, both drawn from
{success, cap_open, tube_drop, ...}. In the paper's notation this is exactly:

    Stratum A (clean / success):  expected_choice == "success"  ->  Y_i = {}
    Stratum B (single failure):   expected_choice == c          ->  Y_i = {c}

Single-choice collection cannot produce Stratum C (multi-failure items), so the
cascade parameter Delta_m of M3 is *not identifiable* from this data. That is
why this script fits only M1 and M2. To unlock M3 you would need to switch to
the per-subtype binary collection of section 7 (one "is there a {c} error?"
question per (video, subtype)) with genuine multi-error videos.

We turn single-choice predictions into the per-(model, item, subtype) binary
flag tensor y[m,i,c] required by the model via one-hot encoding of the
prediction:

    y[m,i,c] = 1  iff  predicted_choice(m,i) == c        (c ranges over FAILURES)

A "success" prediction is the all-zero flag vector. For each (m,i,c) cell:
    * positive channel  (c in Y_i):  did the model flag the true subtype? -> recall
    * negative channel  (c not in Y_i): did it false-flag c?              -> FPR

Models
------
Shared hierarchical detection ability (paper Eq. 1):
    theta_det[m,c] = alpha[m] + delta[m,c]
    alpha[m]   ~ ZeroSumNormal(tau_alpha)                 # headline ability
    delta[:,c] ~ ZeroSumNormal(sigma_c)                   # per-subtype deviation
    a_c > 0  (discrimination),  b_c (difficulty)

M1 - hierarchical multidim 2PL on accuracy (paper Eq. just below 1):
    P(y=1 | c in Y_i)     = sigmoid( a_c (theta_det[m,c] - b_c) )
    P(y=1 | c not in Y_i) = 1 - sigmoid( a_c (theta_det[m,c] - b_c) )
    -> positives and negatives share one logit; no criterion, no FPR freedom.

M2 - two-channel SDT-IRT + per-model criterion (paper Eq. 2):
    P(y=1 | c in Y_i)     = sigmoid( a_c (theta_det[m,c] - b_c) - theta_crit[m] )
    P(y=1 | c not in Y_i) = sigmoid( -theta_crit[m] - b_neg_c )
    theta_crit[m] ~ ZeroSumNormal(tau_crit)   (+ = cautious, - = trigger-happy)
    b_neg_c       = per-subtype clean-pool false-alarm baseline

Inference is PyMC NUTS (matching the paper). We compute pointwise
log-likelihood and select between M1 and M2 by WAIC (lower is better).

Two-stage pipeline
------------------
Stage 1 (``build_flag_table.py``) digests the raw runs -- single-choice,
multi-label P3, or P6-parsed P2 -- into one tidy ``detections_long.csv`` (one row
per model x task x sample x subtype, with ``is_present`` / ``flagged``). Stage 2
(this script) fits M1/M2 directly from that table via ``--table``. The legacy
``--input`` path (raw single-choice ``per_sample_predictions.csv``) is kept for
back-compat, but ``--table`` is preferred and is the only path that supports
multi-error items.

Usage
-----
    # Stage 1: raw runs -> detection table
    python build_flag_table.py --runs-root runs --outdir runs/processed

    # Stage 2: fit M1/M2 from the table
    python fit_sdt_irt.py \
        --table runs/processed/detections_long.csv \
        --outdir results/<analysis_label> \
        --draws 1000 --tune 1000 --chains 2

Outputs (written to --outdir):
    model_selection_waic.csv      M1 vs M2 WAIC comparison
    model_leaderboard.csv         per-model headline numbers (alpha, recall@5%FPR, criterion)
    per_model_subtype.csv         per (model, subtype) reporting quantities + 94% HDI
    idata_M1.nc, idata_M2.nc      full posteriors (ArviZ NetCDF)
    fit_summary.md                human-readable summary of the run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Canonical failure subtypes for the vortexing task (mirrors prompts/PROMPT_CATALOG.md;
# repeated_steps removed).
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
HEADLINE_FPR = 0.05  # cross-model counterfactual operating point (paper headline)


# --------------------------------------------------------------------------- #
# Data loading: single-choice CSV -> flag tensor
# --------------------------------------------------------------------------- #
def load_flag_tensor(csv_path: Path, keep_parse_errors: bool = False):
    """Return (y, is_pos, models, subtypes, items, truth) built from the CSV.

    y      : (N,) int  observed flags, one row per (model, item, subtype) cell
    is_pos : (N,) bool whether subtype c is truly present in item i (c in Y_i)
    model_idx, subtype_idx : (N,) int indices into ``models`` / ``subtypes``
    """
    df = pd.read_csv(csv_path)
    required = {"model", "sample_id", "expected_choice", "predicted_choice"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    # Drop unusable predictions (parse errors / empty) unless asked to keep them.
    df["predicted_choice"] = df["predicted_choice"].fillna("").astype(str)
    df["expected_choice"] = df["expected_choice"].astype(str)
    if "status" in df.columns and not keep_parse_errors:
        df = df[df["status"].fillna("completed") == "completed"]
    df = df[df["predicted_choice"] != ""]

    models = sorted(df["model"].unique())

    # Subtypes = canonical failure labels that actually appear in truth or preds.
    seen = set(df["expected_choice"]) | set(df["predicted_choice"])
    subtypes = [c for c in DEFAULT_FAILURE_LABELS if c in seen]
    # Include any unexpected failure labels not in the canonical list (defensive).
    extra = sorted(
        s for s in seen
        if s not in DEFAULT_FAILURE_LABELS and s != SUCCESS_LABEL and s != ""
    )
    subtypes = subtypes + extra

    # Ground truth per item (consistent across models); items sorted for stability.
    truth_by_item = (
        df.groupby("sample_id")["expected_choice"].agg(lambda s: s.iloc[0]).to_dict()
    )
    items = sorted(truth_by_item)

    m_index = {m: i for i, m in enumerate(models)}
    c_index = {c: i for i, c in enumerate(subtypes)}
    i_index = {it: i for i, it in enumerate(items)}

    # Prediction lookup: (model, item) -> predicted label
    pred = {
        (r.model, r.sample_id): r.predicted_choice
        for r in df.itertuples(index=False)
    }

    rows_y, rows_pos, rows_m, rows_c = [], [], [], []
    for m in models:
        for it in items:
            truth = truth_by_item[it]
            p = pred.get((m, it))
            if p is None:
                continue  # this model has no usable row for this item
            for c in subtypes:
                rows_m.append(m_index[m])
                rows_c.append(c_index[c])
                rows_pos.append(1 if truth == c else 0)
                rows_y.append(1 if p == c else 0)

    out = {
        "y": np.array(rows_y, dtype="int8"),
        "is_pos": np.array(rows_pos, dtype="int8"),
        "model_idx": np.array(rows_m, dtype="int32"),
        "subtype_idx": np.array(rows_c, dtype="int32"),
        "models": models,
        "subtypes": subtypes,
        "items": items,
        "truth_by_item": truth_by_item,
    }
    return out


def load_flag_tensor_from_table(flags_csv: Path, keep_parse_errors: bool = False):
    """Return the flag tensor built directly from Stage-1 ``detections_long.csv``.

    This is the canonical Stage 2 input: ``build_flag_table.py`` already turned
    the raw runs (single-choice OR multi-label OR p6-parsed p2) into one tidy row
    per (model, sample_id, subtype) with ``is_present`` / ``flagged`` columns, so
    here we only index and stack -- no schema-specific one-hot logic. Multi-error
    items are supported natively because ``is_present`` can be 1 for several
    subtypes of the same item.
    """
    df = pd.read_csv(flags_csv)
    required = {"model", "sample_id", "subtype", "is_present", "flagged"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"flag table missing required columns: {sorted(missing)}. "
            "Produce it with build_flag_table.py first."
        )

    if "status" in df.columns and not keep_parse_errors:
        df = df[df["status"].fillna("completed") == "completed"]
    if "outcome_pred" in df.columns:
        df = df[df["outcome_pred"].fillna("") != "ambiguous"]

    models = sorted(df["model"].unique())
    seen = set(df["subtype"].unique())
    subtypes = [c for c in DEFAULT_FAILURE_LABELS if c in seen]
    subtypes += sorted(s for s in seen if s not in DEFAULT_FAILURE_LABELS)
    df = df[df["subtype"].isin(subtypes)].copy()
    items = sorted(df["sample_id"].unique())

    m_index = {m: i for i, m in enumerate(models)}
    c_index = {c: i for i, c in enumerate(subtypes)}

    y = df["flagged"].astype("int8").to_numpy()
    is_pos = df["is_present"].astype("int8").to_numpy()
    model_idx = df["model"].map(m_index).astype("int32").to_numpy()
    subtype_idx = df["subtype"].map(c_index).astype("int32").to_numpy()

    # Per-subtype prevalence from unique (sample, subtype) cells (multi-label safe).
    one = df.drop_duplicates(subset=["sample_id", "subtype"])
    prevalence = np.array(
        [float(one.loc[one["subtype"] == c, "is_present"].mean()) for c in subtypes]
    )

    return {
        "y": y,
        "is_pos": is_pos,
        "model_idx": model_idx,
        "subtype_idx": subtype_idx,
        "models": models,
        "subtypes": subtypes,
        "items": items,
        "prevalence": prevalence,
    }


def benchmark_prevalence(data) -> np.ndarray:
    """Per-subtype positive prevalence implied by the collected items."""
    if "prevalence" in data:
        return data["prevalence"]
    truths = list(data["truth_by_item"].values())
    n_items = len(truths)
    prev = np.array(
        [sum(t == c for t in truths) / max(n_items, 1) for c in data["subtypes"]]
    )
    return prev


# --------------------------------------------------------------------------- #
# Model construction
# --------------------------------------------------------------------------- #
def build_model(data, variant: str):
    import pymc as pm
    import pytensor.tensor as pt

    M = len(data["models"])
    C = len(data["subtypes"])

    midx = data["model_idx"]
    cidx = data["subtype_idx"]
    is_pos = data["is_pos"].astype("float64")
    y = data["y"].astype("int8")

    with pm.Model() as model:
        # --- shared hierarchical detection ability ---
        tau_alpha = pm.HalfNormal("tau_alpha", sigma=1.0)
        alpha = pm.ZeroSumNormal("alpha", sigma=tau_alpha, shape=(M,))

        sigma_c = pm.HalfNormal("sigma_c", sigma=1.0, shape=(C,))
        # delta has shape (C, M); sum-to-zero over the model axis (last axis).
        delta = pm.ZeroSumNormal(
            "delta", sigma=sigma_c[:, None], shape=(C, M), n_zerosum_axes=1
        )
        theta_det = pm.Deterministic("theta_det", alpha[None, :] + delta)  # (C, M)

        a = pm.LogNormal("a", mu=0.0, sigma=0.4, shape=(C,))      # discrimination > 0
        b = pm.Normal("b", mu=0.0, sigma=1.5, shape=(C,))         # difficulty

        # per-cell discriminated ability term  z = a_c (theta_det[c,m] - b_c)
        z = a[cidx] * (theta_det[cidx, midx] - b[cidx])

        if variant == "M1":
            # positives use +z, negatives use -z (shared logit / accuracy form)
            sign = 2.0 * is_pos - 1.0
            p = pm.math.sigmoid(sign * z)

        elif variant == "M2":
            tau_crit = pm.HalfNormal("tau_crit", sigma=1.0)
            theta_crit = pm.ZeroSumNormal("theta_crit", sigma=tau_crit, shape=(M,))
            b_neg = pm.Normal("b_neg", mu=0.0, sigma=1.5, shape=(C,))  # clean-pool FA baseline

            p_pos = pm.math.sigmoid(z - theta_crit[midx])
            p_neg = pm.math.sigmoid(-theta_crit[midx] - b_neg[cidx])
            p = pt.switch(is_pos > 0.5, p_pos, p_neg)
        else:
            raise ValueError(f"unknown variant {variant!r}")

        p = pm.Deterministic("p", p)
        pm.Bernoulli("obs", p=p, observed=y)

    return model


# --------------------------------------------------------------------------- #
# Reporting quantities derived from the M2 posterior
# --------------------------------------------------------------------------- #
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def f1_from_recall_fpr(recall, fpr, pi):
    """Paper Eq. 4: per-subtype F1 at deployment prevalence pi."""
    denom = pi * (recall + 1.0) + (1.0 - pi) * fpr
    return np.where(denom > 0, 2.0 * pi * recall / denom, 0.0)


def summarize_M2(idata, data, prevalences: dict[str, np.ndarray]):
    """Compute per-(model, subtype) reporting quantities with 94% HDI.

    prevalences: dict name -> array of length C (e.g. {"bench":.., "p05":..}).
    Returns a tidy DataFrame.
    """
    import arviz as az

    post = idata.posterior
    models = data["models"]
    subtypes = data["subtypes"]

    # stack chain+draw -> sample axis. Shapes: (S, C, M) for theta_det.
    def flat(name):
        return post[name].stack(sample=("chain", "draw")).values

    theta_det = flat("theta_det")          # (C, M, S)
    a = flat("a")                          # (C, S)
    b = flat("b")                          # (C, S)
    b_neg = flat("b_neg")                  # (C, S)
    theta_crit = flat("theta_crit")        # (M, S)

    def hdi_mean(samples):
        m = float(np.mean(samples))
        h = az.hdi(samples, hdi_prob=0.94)
        return m, float(h[0]), float(h[1])

    rows = []
    logit_fstar = np.log(HEADLINE_FPR / (1.0 - HEADLINE_FPR))
    for ci, c in enumerate(subtypes):
        for mi, m in enumerate(models):
            z = a[ci] * (theta_det[ci, mi] - b[ci])            # (S,)
            recall = _sigmoid(z - theta_crit[mi])              # native recall
            fpr = _sigmoid(-theta_crit[mi] - b_neg[ci])        # clean-pool FPR
            # counterfactual recall at fixed cross-model FPR = HEADLINE_FPR:
            # theta_crit* solves sigmoid(-tc* - b_neg)=f*  ->  tc* = -b_neg - logit(f*)
            tc_star = -b_neg[ci] - logit_fstar
            recall_at_fstar = _sigmoid(z - tc_star)
            row = {"model": m, "subtype": c}
            for label, arr in [
                ("theta_det", theta_det[ci, mi]),
                ("recall", recall),
                ("fpr_clean", fpr),
                (f"recall_at_{int(HEADLINE_FPR*100)}pct_fpr", recall_at_fstar),
            ]:
                mu, lo, hi = hdi_mean(arr)
                row[f"{label}_mean"] = mu
                row[f"{label}_hdi_lo"] = lo
                row[f"{label}_hdi_hi"] = hi
            for pname, pvec in prevalences.items():
                f1 = f1_from_recall_fpr(recall, fpr, pvec[ci])
                mu, lo, hi = hdi_mean(f1)
                row[f"f1_{pname}_mean"] = mu
                row[f"f1_{pname}_hdi_lo"] = lo
                row[f"f1_{pname}_hdi_hi"] = hi
            rows.append(row)
    return pd.DataFrame(rows)


def leaderboard(idata_M2, per_subtype_df, data):
    """Per-model headline table: alpha (ability), mean recall@5%FPR, criterion."""
    import arviz as az

    post = idata_M2.posterior
    models = data["models"]
    alpha = post["alpha"].stack(sample=("chain", "draw")).values   # (M, S)
    theta_crit = post["theta_crit"].stack(sample=("chain", "draw")).values  # (M, S)

    col_recall = f"recall_at_{int(HEADLINE_FPR*100)}pct_fpr_mean"
    rows = []
    for mi, m in enumerate(models):
        a_mu = float(np.mean(alpha[mi]))
        a_hdi = az.hdi(alpha[mi], hdi_prob=0.94)
        tc_mu = float(np.mean(theta_crit[mi]))
        tc_hdi = az.hdi(theta_crit[mi], hdi_prob=0.94)
        sub = per_subtype_df[per_subtype_df["model"] == m]
        rows.append({
            "model": m,
            "alpha_detection_mean": a_mu,
            "alpha_hdi_lo": float(a_hdi[0]),
            "alpha_hdi_hi": float(a_hdi[1]),
            "mean_recall_at_5pct_fpr": float(sub[col_recall].mean()),
            "criterion_theta_crit_mean": tc_mu,
            "criterion_hdi_lo": float(tc_hdi[0]),
            "criterion_hdi_hi": float(tc_hdi[1]),
        })
    df = pd.DataFrame(rows).sort_values(
        "mean_recall_at_5pct_fpr", ascending=False
    ).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    return df


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--table", type=Path,
                     help="detections_long.csv from build_flag_table.py (Stage 1). Preferred input.")
    src.add_argument("--input", type=Path,
                     help="legacy: raw per_sample_predictions.csv (single-choice). "
                          "Prefer --table for the multi-label / p6 pipeline.")
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--tune", type=int, default=1000)
    ap.add_argument("--chains", type=int, default=2)
    ap.add_argument("--target-accept", type=float, default=0.9)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--deploy-prevalence", type=float, default=0.05,
                    help="lab-stream prevalence for the derived F1 (paper uses 0.05)")
    ap.add_argument("--keep-parse-errors", action="store_true")
    args = ap.parse_args(argv)

    import pymc as pm
    import arviz as az

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.table:
        data = load_flag_tensor_from_table(args.table, keep_parse_errors=args.keep_parse_errors)
        input_desc = f"{args.table} (detection table)"
    else:
        data = load_flag_tensor(args.input, keep_parse_errors=args.keep_parse_errors)
        input_desc = f"{args.input} (raw single-choice CSV)"
    M, C, I = len(data["models"]), len(data["subtypes"]), len(data["items"])
    n_cells = len(data["y"])
    print(f"[data] models={M} subtypes={C} items={I} cells={n_cells}")
    print(f"[data] models: {data['models']}")
    print(f"[data] subtypes: {data['subtypes']}")

    bench_prev = benchmark_prevalence(data)
    prevalences = {
        "bench": bench_prev,
        f"p{int(args.deploy_prevalence*100):02d}": np.full(C, args.deploy_prevalence),
    }

    idatas = {}
    for variant in ("M1", "M2"):
        print(f"\n[fit] sampling {variant} ...")
        model = build_model(data, variant)
        with model:
            idata = pm.sample(
                draws=args.draws, tune=args.tune, chains=args.chains,
                target_accept=args.target_accept, random_seed=args.seed,
                progressbar=False, idata_kwargs={"log_likelihood": True},
            )
        idatas[variant] = idata
        idata.to_netcdf(args.outdir / f"idata_{variant}.nc")

    # --- WAIC model selection ---
    comp = az.compare(idatas, ic="waic")
    comp.to_csv(args.outdir / "model_selection_waic.csv")
    print("\n[waic]\n", comp[["rank", "elpd_waic", "p_waic", "elpd_diff", "dse"]])

    # --- reporting from M2 (the criterion-separated model) ---
    per_sub = summarize_M2(idatas["M2"], data, prevalences)
    per_sub.to_csv(args.outdir / "per_model_subtype.csv", index=False)

    board = leaderboard(idatas["M2"], per_sub, data)
    board.to_csv(args.outdir / "model_leaderboard.csv", index=False)
    print("\n[leaderboard]\n", board.to_string(index=False))

    # --- human-readable summary ---
    waic_better = comp.index[0]
    dwaic = float(comp["elpd_diff"].iloc[1]) if len(comp) > 1 else 0.0
    dse = float(comp["dse"].iloc[1]) if len(comp) > 1 else 0.0
    lines = [
        "# SDT-IRT fit summary (M1, M2)\n",
        f"- Input: `{input_desc}`",
        f"- Models (M={M}): {', '.join(data['models'])}",
        f"- Subtypes (C={C}): {', '.join(data['subtypes'])}",
        f"- Items (I={I}), flag-tensor cells (N={n_cells})",
        f"- NUTS: {args.chains} chains, {args.draws} draws / {args.tune} tune, "
        f"target_accept={args.target_accept}\n",
        "## Model selection (WAIC, higher elpd = better)\n",
        comp[["rank", "elpd_waic", "p_waic", "elpd_diff", "dse"]].to_markdown(),
        "",
        f"WAIC prefers **{waic_better}** "
        f"(elpd_diff={dwaic:.1f}, dse={dse:.1f} vs the other model).",
        "A difference large relative to its standard error (dse) is strong",
        "evidence that the criterion family of M2 pays for itself.\n",
        "## Headline leaderboard (from M2)\n",
        board.to_markdown(index=False),
        "",
        "Ability column `alpha_detection_mean` is the criterion-free leaderboard",
        "entry; `mean_recall_at_5pct_fpr` is the cross-model headline metric;",
        "`criterion_theta_crit_mean` is a diagnostic (+ cautious, - trigger-happy),",
        "not an ability score.\n",
        "See `per_model_subtype.csv` for per-(model, subtype) recall, clean-pool",
        "FPR, counterfactual recall@5%FPR, and SDT-IRT F1 at benchmark and 5%",
        "prevalence, each with a 94% HDI.",
    ]
    (args.outdir / "fit_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[done] wrote outputs to {args.outdir}")


if __name__ == "__main__":
    sys.exit(main())
