# Cosmos Local Setup

The current NVIDIA/Cosmos repository centers on Cosmos 3. For LabOS-Sim
evaluation, the relevant surface is Cosmos 3 Reasoner because it accepts text,
image, and video inputs and returns text. Generator mode is not needed for the
vortexing benchmark.

Sources:

- https://github.com/NVIDIA/Cosmos
- https://github.com/NVIDIA/Cosmos/blob/main/README.md

## Recommended Local Endpoint

Use the Cosmos 3 Reasoner NIM container when possible. It exposes an
OpenAI-compatible endpoint at:

```text
http://127.0.0.1:8000/v1
```

The repo documents two served model names:

```text
nvidia/cosmos3-nano-reasoner
nvidia/cosmos3-super-reasoner
```

The scaffold contains disabled configs for both:

```yaml
cosmos3_reasoner_nano_local
cosmos3_reasoner_super_local
```

Enable one only after the local server is running.

## NIM Launch Shape

The NVIDIA README shows this launch pattern:

```bash
export CONTAINER_NAME="nvidia-cosmos3-reasoner"
export IMG_NAME="nvcr.io/nim/nvidia/cosmos3-reasoner:1.7.0"
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p "$LOCAL_NIM_CACHE"

docker run -it --rm --name=$CONTAINER_NAME \
  --runtime=nvidia \
  --gpus all \
  --shm-size=32GB \
  -e NGC_API_KEY=$NGC_API_KEY \
  -e NIM_MODEL_SIZE=nano \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -u $(id -u) \
  -p 8000:8000 \
  $IMG_NAME
```

Use `NIM_MODEL_SIZE=super` for the larger model if hardware allows.

## vLLM Launch Shape

The repo also documents vLLM serving:

```bash
vllm serve nvidia/Cosmos3-Nano \
  --hf-overrides '{"architectures": ["Cosmos3ReasonerForConditionalGeneration"]}' \
  --async-scheduling \
  --allowed-local-media-path / \
  --port 8000
```

For full-frame consideration before sampling, the repo notes:

```bash
--media-io-kwargs '{"video": {"num_frames": -1}}'
```

The LabOS adapter sends local videos as `file://` URLs, so
`--allowed-local-media-path /` is required for vLLM.

## Benchmark Defaults

The Cosmos adapter uses the OpenAI-compatible endpoint and passes video sampling
through request body extras:

```yaml
extra_body:
  extra_body:
    media_io_kwargs:
      video:
        fps: 4.0
```

This follows the current Cosmos README guidance for `media_io_kwargs`. For
evidence-normalized comparisons, run a separate standardized frame/contact-sheet
condition across all models; for interface-native comparisons, Cosmos should use
direct video at the documented 4 fps sampling.

## Practical Notes

- Cosmos local setup requires Linux, NVIDIA GPUs, Docker or a compatible vLLM
  environment, and model access credentials.
- The repo recommends matching CUDA and vLLM versions carefully. CUDA 13 uses
  `vllm==0.21.0`; CUDA 12.8 uses `vllm==0.19.1`.
- This project does not install Cosmos dependencies automatically because they
  are large, hardware-specific, and require external credentials.
