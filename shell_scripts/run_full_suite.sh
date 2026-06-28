#!/usr/bin/env bash
# Full benchmark run across all models, then process + render.
# Edit MODELS / CAMS / CONC / RUN_ID as needed. Run from anywhere; it cd's to root.
set -euo pipefail
cd "$(dirname "$0")/.."

MODELS=(gemini_3_1_pro gpt_5_5 claude_opus_4_8 qwen3_vl)   # VLMs (config/models.yaml)
PARSER_LLM=gpt_5_5_parser                                  # text LLM for P6
CAMS=(front gripper)                                       # camera angles to send
CONC=4                                                     # parallel clips per model
RUN_ID="${RUN_ID:-full_01}"                                # groups this run under runs/raw/{RUN_ID}/
LABEL="${LABEL:-vortexing_v1}"                             # results/{LABEL}/
OP=vortex

echo "== build the full run list (all datasets) =="
mkdir -p data
cat data/*/metadata.jsonl > data/full_run_list.jsonl
DATA=data/full_run_list.jsonl

echo "===== EASY level: P1 (closed binary) + P3 (multilabel) ====="
python scripts/data_collection/run_closed_binary.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" \
    --camera-views "${CAMS[@]}" --concurrency "$CONC"
python scripts/data_collection/run_multilabel_classification.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" \
    --camera-views "${CAMS[@]}" --concurrency "$CONC"

echo "===== MIDDLE level: P2 (open detection) -> P6 (parser) ====="
python scripts/data_collection/run_open_detection.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" \
    --camera-views "${CAMS[@]}" --concurrency "$CONC"
# Parse every P2 run dir under this run_id with the parsing LLM.
for d in runs/raw/"$RUN_ID"/"${OP}"_open_detection/*/; do
    python scripts/data_collection/run_freetext_parser.py \
        --llms "$PARSER_LLM" --p2-run-dir "$d" --concurrency "$CONC"
done

echo "===== PROCESS + RENDER ====="
python scripts/data_processing/build_flag_table.py --runs-root runs --outdir runs/processed
python scripts/results_rendering/report_stats.py \
    --table runs/processed/detections_long.csv --by-task --outdir "results/$LABEL"
python scripts/results_rendering/fit_sdt_irt.py \
    --table runs/processed/detections_long.csv --outdir "results/$LABEL"
python scripts/results_rendering/summarize_cost.py --runs-root runs --outdir runs/processed

echo "Done. See results/$LABEL/ and runs/processed/."
