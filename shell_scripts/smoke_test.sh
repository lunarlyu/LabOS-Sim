#!/usr/bin/env bash
# Cheap end-to-end validation of the live collection path: one model, a few clips,
# two camera angles. Run from anywhere; it cd's to the repo root.
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-gemini_3_1_pro}"   # override: MODEL=gpt_5_5 ./shell_scripts/smoke_test.sh
LIMIT="${LIMIT:-3}"

echo "== P3 multilabel: $MODEL on $LIMIT clips, front+gripper angles =="
python scripts/data_collection/run_multilabel_classification.py \
    --models "$MODEL" --limit "$LIMIT" --camera-views front gripper --concurrency 2

echo "== build flag table =="
python scripts/data_processing/build_flag_table.py \
    --runs-root runs --metadata metadata/real_human_samples_no_multiple.json \
    --outdir runs/processed

echo "== direct stats + cost =="
python scripts/results_rendering/report_stats.py --flags runs/processed/flags_long.csv --outdir results/smoke
python scripts/results_rendering/summarize_cost.py --runs-root runs --outdir runs/processed
echo "Smoke test complete. Inspect runs/raw/, runs/processed/flags_long.csv, results/smoke/."
