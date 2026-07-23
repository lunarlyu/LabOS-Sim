#!/usr/bin/env bash
# Cheap end-to-end validation of the live collection path: one model, a few clips,
# the full-eval camera angles. Run from anywhere; it cd's to eval/.
set -euo pipefail
EVAL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_ROOT="$(cd "$EVAL_ROOT/.." && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
cd "$EVAL_ROOT"

MODEL="${MODEL:-gemini_3_1_pro}"   # override: MODEL=gpt_5_5 eval/scripts/workflows/smoke_test.sh
LIMIT="${LIMIT:-3}"
RUN_ID="${RUN_ID:-smoke_01}"

echo "== build a tiny run list ($LIMIT clips) =="
mkdir -p ../data
head -n "$LIMIT" ../data/real_human/metadata.jsonl > ../data/smoke_run_list.jsonl

echo "== P2 multilabel: $MODEL, front+left+right angles, run_id=$RUN_ID =="
"$PYTHON" scripts/data_collection/run_multilabel_classification.py \
    --models "$MODEL" --data ../data/smoke_run_list.jsonl --run-id "$RUN_ID" \
    --camera-views front left right --concurrency 2

echo "== build detection table =="
"$PYTHON" scripts/data_processing/build_detection_table.py \
    --runs-root runs --run-ids "$RUN_ID" --outdir runs/processed

echo "== direct stats + cost =="
"$PYTHON" scripts/results_rendering/report_stats.py --table runs/processed/detections_long.csv --outdir results/smoke
"$PYTHON" scripts/results_rendering/summarize_cost.py \
    --runs-root runs --run-id "$RUN_ID" --outdir runs/processed
echo "Smoke test complete. Inspect runs/raw/$RUN_ID/, runs/processed/detections_long.csv, results/smoke/."
