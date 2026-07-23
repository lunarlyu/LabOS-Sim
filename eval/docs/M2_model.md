# The M2 model: signal-detection IRT for VLM failure detection

This note explains the model the benchmark fits (`scripts/results_rendering/fit_sdt_irt.py`):
what it is, what it measures, why it is better than reporting raw F1/AUROC, how
to read every parameter, and how it is fitted. It is the M2 model of the design
note *"Signal-Detection IRT for AI Evaluation on Success-vs-Multi-Failure Tasks"*
(Lyu & Tan), as applied to our vortexing data.

## 1. The observable

For model `m`, clip `i`, and failure subtype `c`, we have a binary flag

```
y[m, i, c] ∈ {0, 1}   = "did model m say subtype c is present in clip i?"
```

Each clip carries a ground-truth error set `Y_i`. Every `(m, i, c)` cell sits on
one of two **channels**:

- **positive channel** — `c` is truly present (`c ∈ Y_i`): flagging it is a *hit*
  (this is recall / sensitivity);
- **negative channel** — `c` is truly absent (`c ∉ Y_i`): flagging it is a *false
  alarm* (false-positive rate).

Success clips (`Y_i = {}`) contribute only negative cells across all subtypes, so
"recognizing success" is exactly behavior on the negative channel; "recognizing a
failure" is behavior on the positive channel for that subtype. `build_detection_table.py`
produces this tensor as `detections_long.csv`; `fit_sdt_irt.py` consumes it.

## 2. The two models

Both share a hierarchical detection-ability decomposition:

```
theta_det[m, c] = alpha[m] + delta[m, c]
```

`alpha[m]` is model `m`'s overall ability; `delta[m, c]` is its per-subtype
deviation. Each subtype has a discrimination `a_c > 0` and difficulty `b_c`.

**M1 — hierarchical 2PL on accuracy (baseline).** Positives and negatives are
mirror images of one logit; there is no decision criterion:

```
P(y = 1 | c present) = sigmoid( a_c · (theta_det[m,c] − b_c) )
P(y = 1 | c absent ) = 1 − sigmoid( a_c · (theta_det[m,c] − b_c) )
```

Because recall and FPR are tied to the same logit, M1 cannot tell a careful model
from a trigger-happy one: a model that flags everything gets the same high ability
as a model that genuinely discriminates.

**M2 — two-channel SDT-IRT with a per-model criterion.** M2 keeps the ability core
but gives the two channels separate expressions and inserts a per-model criterion
`theta_crit[m]`, entering with **opposite signs**:

```
P(y = 1 | c present) = sigmoid( a_c · (theta_det[m,c] − b_c) − theta_crit[m] )
P(y = 1 | c absent ) = sigmoid( −theta_crit[m] − b_neg_c )
```

That sign flip is the whole point: a cautious model (`theta_crit > 0`) gets *both*
lower recall and lower false-alarm rate. M2 thus factors performance into **how
well a model sees errors** (`theta_det`, driven by `alpha`) versus **how willing
it is to flag** (`theta_crit`) — the signal-detection split of d′ from criterion.
The negative channel depends only on the criterion and a per-subtype baseline
`b_neg_c`, not on ability — seeing errors well does not help on a clip with no
error.

M2 is M1 plus one parameter family (the criterion and its clean-pool baseline);
in the design note this is the nested chain M1 ⊂ M2 (⊂ M3, which needs multi-error
clips we do not yet collect).

## 3. Parameters and how to read them

| Symbol | Shape | Meaning / interpretation |
|---|---|---|
| `alpha[m]` | M | **Headline ability.** Higher = genuinely sees errors better, averaged over subtypes. The criterion-free leaderboard number. |
| `delta[m,c]` | M×C | Per-subtype deviation: `+` strong on `c` relative to its own average, `−` weak. "Great at dropped tubes, blind to an off vortex." |
| `theta_det[m,c]` | M×C | Total per-subtype ability = `alpha + delta`; plays the role of d′. |
| `a_c` | C | **Discrimination**: how sharply ability separates hits from misses. Large = the subtype cleanly ranks good vs bad models. |
| `b_c` | C | **Difficulty**: ability at which a model has 50/50 recall when the error is present. High = intrinsically hard to see. |
| `theta_crit[m]` | M | **Criterion / operating point.** `+` cautious (lower recall *and* FPR), `−` trigger-happy. A diagnostic, NOT an ability. |
| `b_neg_c` | C | **Clean-pool false-alarm baseline** for subtype `c`. Clean FPR = `sigmoid(−theta_crit − b_neg_c)`. |
| `tau_alpha`, `sigma_c`, `tau_crit` | scalars/C | Hierarchy spreads (how much models differ in ability; how much subtype `c` adds model-specific signal; spread of operating points). The variance-reduction levers. |

Key reading rule: a low native F1 from a high `theta_crit` (too cautious) is a
*different* problem from a low F1 from low `alpha` (can't see the error). M2 tells
them apart; F1 alone cannot.

## 4. What M2 reports, and how it covers the statistics

From the posterior, `fit_sdt_irt.py` derives (each with a 94% credible interval):

- **per-subtype recall** = `sigmoid(a_c(theta_det − b_c) − theta_crit)`
- **clean-pool FPR** = `sigmoid(−theta_crit − b_neg_c)`
- **SDT-IRT F1 at prevalence π** = `2π·recall / (π(recall+1) + (1−π)·FPR)`,
  reported at the benchmark's own prevalence and at a deployment prevalence (5%).
- **counterfactual recall at a fixed 5% FPR** — slide every model to the criterion
  that yields 5% FPR (`theta_crit* = −b_neg_c − logit(0.05)`) and read its recall.
  This is the headline cross-model metric: it ranks models by *ability* after
  removing differences in caution.
- **leaderboard**: per model `alpha` (ability), mean recall@5%FPR, and the
  criterion as a diagnostic.

So every classical quantity (recall, FPR, F1) is recoverable, but as *functions of
the fitted parameters* — meaning you can recompute them at any operating point or
prevalence, not just the one the benchmark happened to have.

## 5. Why this beats reporting raw F1 / AUROC per subtype

1. **Disentangles ability from operating point.** Raw F1 conflates "can't see it"
   with "saw it but didn't flag it"; AUROC throws the operating point away
   entirely. M2 gives `alpha` (ability) and `theta_crit` (caution) separately and
   lets you reconstruct F1 at any threshold.
2. **Statistical efficiency via partial pooling.** Thinly-sampled subtypes
   (e.g. `tube_empty`, `wrong_orientation` with ~a dozen clips) borrow strength
   through the hierarchy (`sigma_c` shrinks them toward the model's overall
   `alpha`), turning unstable point estimates into usable intervals.
3. **Separates subtype properties from model properties.** `a_c`/`b_c` describe
   the *subtype* (is it hard for everyone?); `delta[m,c]` describes the *model*.
   A raw F1 table bundles these.
4. **One principled headline with uncertainty.** `alpha` answers "which VLM is
   best at catching mistakes?" without arbitrarily averaging per-subtype F1s, and
   everything carries credible intervals.
5. **Prevalence robustness.** F1 depends on prevalence, which here is a collection
   artifact. M2 recomputes at any deployment prevalence; a fixed F1 table cannot.

The cost is the modeling assumptions in §7; that is why model selection is done by
WAIC and everything is reported with intervals rather than asserted.

## 6. Fitting methodology

`fit_sdt_irt.py` builds the model in PyMC and samples with NUTS.

- **Priors (partial pooling).** `alpha`, `delta`, `theta_crit` are zero-mean
  Gaussians whose spreads (`tau_alpha`, `sigma_c`, `tau_crit`) are themselves
  estimated (half-normal), so the data decide how much each subtype/model deviates.
  Sum-to-zero constraints (`ZeroSumNormal`) over the model axis make `alpha`,
  `delta`, `theta_crit` identifiable. `a_c` is log-normal (positive); `b_c`,
  `b_neg_c` are normal.
- **Likelihood.** Each cell is `Bernoulli(p)` with `p` from the M1 or M2 equation
  above; the pointwise log-likelihood is stored for model comparison.
- **Inference.** NUTS, 2 chains, `target_accept = 0.9` (raise to 0.95 if
  divergences persist), configurable draws/tune.
- **Model selection.** M1 vs M2 by **WAIC** (Widely Applicable Information
  Criterion): out-of-sample predictive accuracy with an effective-parameters
  penalty, correct for hierarchical models. A WAIC gap large relative to its
  standard error means the criterion family of M2 earns its keep.
- **Outputs.** `model_selection_waic.csv`, `model_leaderboard.csv`,
  `per_model_subtype.csv` (all reporting quantities with HDIs), `fit_summary.md`,
  and the posteriors `idata_M1.nc` / `idata_M2.nc`.

Run:

```
cd eval
python scripts/data_processing/build_detection_table.py \
    --runs-root runs --outdir runs/processed
python scripts/results_rendering/fit_sdt_irt.py \
    --table runs/processed/detections_long.csv --outdir results/<analysis_label>
```

## 7. Assumptions and limitations

1. **Conditional independence** of flags given the parameters (no per-clip random
   effect yet — a natural extension if some clips are uniformly hard).
2. **One `a_c`, `b_c` per subtype**, shared across models (difficulty is a property
   of the subtype).
3. **Logistic link** (SDT with logistic latent noise); `theta_det` ≈ d′,
   `theta_crit` ≈ criterion.
4. **A single per-model criterion** governs caution across all subtypes; subtypes
   differ in baseline false-alarm only through `b_neg_c`.
5. **Negatives are exchangeable** — clean (success) negatives and
   "some-other-error-present" negatives are treated alike. Relaxing this is the
   cascade model M3, which needs genuine multi-error clips (not yet collected).
6. **Confidence is not used** in the hard-flag fit; it is the natural input to a
   graded-response extension (M2-G) and is recorded for that purpose.

## 8. Validation status

The model equations and every reported formula were checked by simulation
(empirical hit/false-alarm rates match the model probabilities; the counterfactual
criterion yields exactly 5% FPR; the F1 formula matches a direct confusion count)
and by parameter recovery (inverting the M2 equations from simulated data recovers
`theta_det` at correlation ≈ 0.99 and the criterion to within ~0.04), confirming
the likelihood is correct and identifiable. The full Bayesian NUTS run (with the
hierarchical priors and WAIC) should be executed on a machine with PyMC installed
for a given dataset.
