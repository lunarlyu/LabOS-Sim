#!/usr/bin/env bash
# Full benchmark run across all models, then process + render.
# Edit MODELS / CAMS / CONC / RUN_ID as needed. Run from anywhere; it cd's to eval/.
set -euo pipefail
EVAL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_ROOT="$(cd "$EVAL_ROOT/.." && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
cd "$EVAL_ROOT"

MODELS=(gemini_3_1_pro gpt_5_5 claude_opus_4_8 qwen3_vl)   # VLMs (config/models.yaml)
PARSER_LLM=gpt_5_5_parser                                  # text LLM for P5/P6 parsers
CAMS=(front left right)                                    # fixed camera angles to send
CONC=4                                                     # parallel clips per model
RUN_ID="${RUN_ID:-full_01}"                                # groups this run under runs/raw/{RUN_ID}/
LABEL="${LABEL:-vortexing_v1}"                             # results/{LABEL}/
OP=vortex

echo "== build the full run list (all datasets) =="
mkdir -p ../data
cat ../data/*/metadata.jsonl > ../data/full_run_list.jsonl
DATA=../data/full_run_list.jsonl

echo "===== EASY: P1 (closed binary) + P2 (multi-label) ====="
"$PYTHON" scripts/data_collection/run_closed_binary.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
"$PYTHON" scripts/data_collection/run_multilabel_classification.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"

echo "===== MIDDLE strict: P3 (error-aware) -> P5 parser ====="
"$PYTHON" scripts/data_collection/run_open_detection_strict.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
for d in runs/raw/"$RUN_ID"/"${OP}"_open_detection_strict/*/; do
    "$PYTHON" scripts/data_collection/run_open_detection_strict_parser.py \
        --llms "$PARSER_LLM" --source-run-dir "$d" --concurrency "$CONC"
done

echo "===== MIDDLE free: P4 (error-unaware) -> P6 parser ====="
"$PYTHON" scripts/data_collection/run_open_detection_free.py \
    --models "${MODELS[@]}" --data "$DATA" --run-id "$RUN_ID" --camera-views "${CAMS[@]}" --concurrency "$CONC"
for d in runs/raw/"$RUN_ID"/"${OP}"_open_detection_free/*/; do
    "$PYTHON" scripts/data_collection/run_open_detection_free_parser.py \
        --llms "$PARSER_LLM" --source-run-dir "$d" --concurrency "$CONC"
done

echo "===== PROCESS + RENDER ====="
"$PYTHON" scripts/data_processing/build_detection_table.py \
    --runs-root runs --run-ids "$RUN_ID" --outdir runs/processed
"$PYTHON" scripts/results_rendering/report_stats.py \
    --table runs/processed/detections_long.csv --by-task --outdir "results/$LABEL"
# Fit M2 per task (each model must appear once per (sample, subtype)).
for TASK in "${OP}_multilabel_classification" "${OP}_open_detection_strict_parser" "${OP}_open_detection_free_parser"; do
    "$PYTHON" scripts/results_rendering/fit_sdt_irt.py \
        --table runs/processed/detections_long.csv --task "$TASK" --outdir "results/$LABEL/$TASK"
done
"$PYTHON" scripts/results_rendering/summarize_cost.py \
    --runs-root runs --run-id "$RUN_ID" --outdir runs/processed

echo "Done. See results/$LABEL/ and runs/processed/."
