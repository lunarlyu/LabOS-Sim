#!/usr/bin/env bash
# Full benchmark run across all models, then process + render.
# Edit MODELS / CAMS / CONC / RUN_ID as needed. Run from anywhere; it cd's to root.
set -euo pipefail
cd "$(dirname "$0")/../.."

MODELS=(gemini_3_1_pro gpt_5_5 claude_opus_4_8 qwen3_vl)   # VLMs (config/models.yaml)
PARSER_LLM=gpt_5_5_parser                                  # text LLM for P5/P6 parsers
CAMS=(front left right)                                    # fixed camera angles to send
CONC=4                                                     # parallel clips per model
RUN_ID="${RUN_ID:-full_01}"                                # groups this run under runs/raw/{RUN_ID}/
LABEL="${LABEL:-vortexing_v1}"                             # results/{LABEL}/
OP=vortex

echo "== build the full run list (all datasets) =="
mkdir -p data
cat data/*/metadata.jsonl > data/full_run_list.jsonl
DATA=data/full_run_list.jsonl

echo "===== EASY: P1 (closed binary) + P2 (multi-label) ====="
python scripts/data_collection/run_closed_binary.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
python scripts/data_collection/run_multilabel_classification.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"

echo "===== MIDDLE strict: P3 (error-aware) -> P5 parser ====="
python scripts/data_collection/run_open_detection_strict.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
for d in runs/raw/"$RUN_ID"/"${OP}"_open_detection_strict/*/; do
    python scripts/data_collection/run_open_detection_strict_parser.py \
        --llms "$PARSER_LLM" --source-run-dir "$d" --concurrency "$CONC"
done

echo "===== MIDDLE free: P4 (error-unaware) -> P6 parser ====="
python scripts/data_collection/run_open_detection_free.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
for d in runs/raw/"$RUN_ID"/"${OP}"_open_detection_free/*/; do
    python scripts/data_collection/run_open_detection_free_parser.py \
        --llms "$PARSER_LLM" --source-run-dir "$d" --concurrency "$CONC"
done

echo "===== PROCESS + RENDER ====="
python scripts/data_processing/build_detection_table.py --runs-root runs --outdir runs/processed
python scripts/results_rendering/report_stats.py \
    --table runs/processed/detections_long.csv --by-task --outdir "results/$LABEL"
# Fit M2 per task (each model must appear once per (sample, subtype)).
for TASK in "${OP}_multilabel_classification" "${OP}_open_detection_strict_parser" "${OP}_open_detection_free_parser"; do
    python scripts/results_rendering/fit_sdt_irt.py \
        --table runs/processed/detections_long.csv --task "$TASK" --outdir "results/$LABEL/$TASK"
done
python scripts/results_rendering/summarize_cost.py --runs-root runs --outdir runs/processed

echo "Done. See results/$LABEL/ and runs/processed/."
