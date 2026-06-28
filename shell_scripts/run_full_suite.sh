#!/usr/bin/env bash
# Full benchmark run across all models, then process + render.
# Edit MODELS / CAMS / CONC as needed. Run from anywhere; it cd's to the repo root.
set -euo pipefail
cd "$(dirname "$0")/.."

MODELS=(gemini_3_1_pro gpt_5_5 claude_opus_4_8 qwen3_vl)   # VLMs (config/models.yaml)
PARSER_LLM=gpt_5_5_parser                                  # text LLM for P6
CAMS=(front gripper)                                       # camera angles to send
CONC=4                                                     # parallel clips per model
LABEL="${LABEL:-vortexing_v1}"                             # results/{LABEL}/

echo "===== EASY level: P1 (closed binary) + P3 (multilabel) ====="
python scripts/data_collection/run_closed_binary.py \
    --models "${MODELS[@]}" --camera-views "${CAMS[@]}" --concurrency "$CONC"
python scripts/data_collection/run_multilabel_classification.py \
    --models "${MODELS[@]}" --camera-views "${CAMS[@]}" --concurrency "$CONC"

echo "===== MIDDLE level: P2 (open detection) -> P6 (parser) ====="
python scripts/data_collection/run_open_detection.py \
    --models "${MODELS[@]}" --camera-views "${CAMS[@]}" --concurrency "$CONC"
# Parse every P2 run dir that exists with the parsing LLM.
for d in runs/raw/vortex_open_detection/*/*/; do
    python scripts/data_collection/run_freetext_parser.py \
        --llms "$PARSER_LLM" --p2-run-dir "$d" --concurrency "$CONC"
done

echo "===== PROCESS + RENDER ====="
python scripts/data_processing/build_flag_table.py \
    --runs-root runs --metadata metadata/real_human_samples_no_multiple.json \
    --outdir runs/processed
python scripts/results_rendering/report_stats.py \
    --flags runs/processed/flags_long.csv --by-task --outdir "results/$LABEL"
python scripts/results_rendering/fit_sdt_irt.py \
    --flags runs/processed/flags_long.csv --outdir "results/$LABEL"
python scripts/results_rendering/summarize_cost.py \
    --runs-root runs --outdir runs/processed

echo "Done. See results/$LABEL/ and runs/processed/."
