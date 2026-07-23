#!/usr/bin/env bash
# Cheap end-to-end validation of the live collection path: one model, a few clips,
# the full-eval camera angles. Run from anywhere; it cd's to the repo root.
set -euo pipefail
cd "$(dirname "$0")/../.."

MODEL="${MODEL:-gemini_3_1_pro}"   # override: MODEL=gpt_5_5 eval/scripts/workflows/smoke_test.sh
LIMIT="${LIMIT:-3}"
RUN_ID="${RUN_ID:-smoke_01}"

echo "== build a tiny run list ($LIMIT clips) =="
mkdir -p ../data
head -n "$LIMIT" ../data/real_human/metadata.jsonl > ../data/smoke_run_list.jsonl

echo "== P2 multilabel: $MODEL, front+left+right angles, run_id=$RUN_ID =="
python scripts/data_collection/run_multilabel_classification.py \
    --models "$MODEL" --data ../data/smoke_run_list.jsonl --run-id "$RUN_ID" \
    --camera-views front left right --concurrency 2

echo "== build detection table =="
python scripts/data_processing/build_detection_table.py --runs-root runs --outdir runs/processed

echo "== direct stats + cost =="
python scripts/results_rendering/report_stats.py --table runs/processed/detections_long.csv --outdir results/smoke
python scripts/results_rendering/summarize_cost.py --runs-root runs --outdir runs/processed
echo "Smoke test complete. Inspect runs/raw/$RUN_ID/, runs/processed/detections_long.csv, results/smoke/."
