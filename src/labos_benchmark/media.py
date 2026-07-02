from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path
from typing import Any

import imageio_ffmpeg


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_key(source_sha256: str, kind: str, params: dict[str, Any]) -> str:
    """Content-address a preprocessed output by (source bytes, transform, params).

    Any change to the source clip or the preprocess settings yields a new key, so
    a cached file is only reused when it is byte-for-byte the transform we'd redo.
    """
    blob = json.dumps({"src": source_sha256, "kind": kind, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]



def transcode_video(
    input_path: Path,
    output_path: Path,
    *,
    max_width: int,
    fps: float,
    crf: int,
    preset: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"fps={fps},scale={max_width}:-2",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


def create_contact_sheet(
    input_path: Path,
    output_path: Path,
    *,
    max_width: int,
    fps: float,
    columns: int,
    rows: int,
    quality: int,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"fps={fps},scale={max_width}:-2,tile={columns}x{rows}",
        "-frames:v",
        "1",
        "-q:v",
        str(quality),
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


def maybe_transcode_videos(
    videos: list[dict[str, Any]],
    cache_dir: Path,
    media_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Preprocess each source clip into the API-delivered form, via a shared cache.

    ``cache_dir`` is a single content-addressed cache (not per-run): the output
    filename encodes a hash of the source bytes + transform params, so the same
    clip+settings is transcoded once and then reused across runs, tasks, and
    models. On a cache hit ffmpeg is skipped entirely (the expensive part).
    """
    cache_dir = Path(cache_dir)
    if media_config.get("input_type") == "image_contact_sheet":
        sheet_config = media_config.get("preprocess", {}).get("contact_sheet", {})
        params = {
            "max_width": int(sheet_config.get("max_width", 720)),
            "fps": float(sheet_config.get("fps", 1)),
            "columns": int(sheet_config.get("columns", 4)),
            "rows": int(sheet_config.get("rows", 8)),
            "quality": int(sheet_config.get("quality", 3)),
        }
        processed: list[dict[str, Any]] = []
        for video in videos:
            source_path = Path(video["path"])
            source_sha = file_sha256(source_path)
            key = _cache_key(source_sha, "contact_sheet", params)
            output_path = cache_dir / f"{source_path.stem}.{key}.contact_sheet.jpg"
            if not output_path.is_file():
                create_contact_sheet(source_path, output_path, **params)
            processed.append(
                {
                    **video,
                    "source_path": source_path,
                    "path": output_path,
                    "bytes": output_path.stat().st_size,
                    "sha256": file_sha256(output_path),
                    "api_media": {
                        "preprocessed": True,
                        "source_path": str(source_path),
                        "source_sha256": source_sha,
                        "api_sha256": file_sha256(output_path),
                        "delivery": "base64_image_url",
                        "fairness_profile": media_config.get("fairness_profile"),
                        "contact_sheet": sheet_config,
                    },
                }
            )
        return processed

    transcode_config = media_config.get("preprocess", {}).get("transcode", {})
    if not transcode_config.get("enabled", False):
        return videos

    params = {
        "max_width": int(transcode_config.get("max_width", 480)),
        "fps": float(transcode_config.get("fps", 1)),
        "crf": int(transcode_config.get("crf", 35)),
        "preset": str(transcode_config.get("preset", "veryfast")),
    }
    processed: list[dict[str, Any]] = []
    for video in videos:
        source_path = Path(video["path"])
        source_sha = file_sha256(source_path)
        key = _cache_key(source_sha, "transcode", params)
        output_path = cache_dir / f"{source_path.stem}.{key}.api.mp4"
        if not output_path.is_file():
            transcode_video(source_path, output_path, **params)
        processed.append(
            {
                **video,
                "source_path": source_path,
                "path": output_path,
                "bytes": output_path.stat().st_size,
                "sha256": file_sha256(output_path),
                "api_media": {
                    "preprocessed": True,
                    "source_path": str(source_path),
                    "source_sha256": source_sha,
                    "api_sha256": file_sha256(output_path),
                    "fairness_profile": media_config.get("fairness_profile"),
                    "transcode": transcode_config,
                },
            }
        )
    return processed
