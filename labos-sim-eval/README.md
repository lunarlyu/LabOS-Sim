# LabOS-Sim Eval

Evaluation scaffold for LabOS-Sim procedural error recognition.

This directory is a clean evaluation package shaped after common patterns from:

- GTG2Vid: top-level YAML config plus simple evaluation entrypoint
- VLMEvalKit: model adapters, per-call API logs, and config snapshots
- CaptainCook4D error_recognition: dataset/results CSV workflow
- EgoPER: task-level metrics and preprocessing/splits

The code here is intentionally lightweight for now. It defines the structure,
prompt catalog, adapter boundaries, dataset loader, metrics, run metadata, and
result layout. Provider-specific calls can be filled in adapter-by-adapter.

## Layout

```text
labos-sim-eval/
  config.yaml
  prompts/
  adapters/
  dataset.py
  metrics.py
  prompts_loader.py
  run_metadata.py
  eval.py
  make_splits.py
  results/
```

## Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Dry-run the evaluation skeleton:

```bash
python eval.py --config config.yaml --dry-run
```

For local Cosmos 3 Reasoner setup, see:

```text
docs/cosmos_local_setup.md
```

Outputs are written to:

```text
results/<run_name>/
  config_snapshot.yaml
  run_metadata.json
  predictions.csv
  metrics.csv
  api_logs/
  errors.log
```

## Notes

The default `config.yaml` points at `../metadata/real_human_samples_no_multiple.json`,
which excludes the ambiguous `multiple` condition samples.

Prompt templates are plain `.txt` files so they are easy to version, diff, and
reuse across model backends.

The default model catalog distinguishes the canonical visual evidence from the
adapter transport. The canonical policy is recorded under `media.policy`; each
adapter may convert that evidence into `video_url`, `image_url`, local
`file://` media, or provider-native uploads, but the chosen transport must be
captured in the config snapshot for reproducibility.
