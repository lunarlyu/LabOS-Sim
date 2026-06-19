from __future__ import annotations

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


def maybe_transcode_videos(
    videos: list[dict[str, Any]],
    output_dir: Path,
    media_config: dict[str, Any],
) -> list[dict[str, Any]]:
    transcode_config = media_config.get("preprocess", {}).get("transcode", {})
    if not transcode_config.get("enabled", False):
        return videos

    processed: list[dict[str, Any]] = []
    for video in videos:
        source_path = Path(video["path"])
        output_path = output_dir / f"{source_path.stem}.api.mp4"
        transcode_video(
            source_path,
            output_path,
            max_width=int(transcode_config.get("max_width", 480)),
            fps=float(transcode_config.get("fps", 1)),
            crf=int(transcode_config.get("crf", 35)),
            preset=str(transcode_config.get("preset", "veryfast")),
        )
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
                    "source_sha256": file_sha256(source_path),
                    "api_sha256": file_sha256(output_path),
                    "fairness_profile": media_config.get("fairness_profile"),
                    "transcode": transcode_config,
                },
            }
        )
    return processed
