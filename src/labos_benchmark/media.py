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
    frame_count: int | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if frame_count is not None:
        _source_frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(input_path))
        if seconds <= 0:
            raise ValueError(f"{input_path} has invalid duration {seconds}")
        if columns * rows != frame_count:
            raise ValueError(
                f"contact-sheet grid {columns}x{rows} must equal frame_count={frame_count}"
            )
        # Uniformly cover the full duration with exactly N output frames. FFmpeg's
        # fps filter duplicates frames when a short source has fewer than N; this
        # keeps the model input shape fixed instead of failing those samples.
        target_fps = frame_count / seconds
        video_filter = (
            f"fps={target_fps:.12g},trim=end_frame={frame_count},"
            f"scale={max_width}:-2,tile={columns}x{rows}"
        )
    else:
        video_filter = f"fps={fps},scale={max_width}:-2,tile={columns}x{rows}"

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        video_filter,
        "-frames:v",
        "1",
        "-q:v",
        str(quality),
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path


def extract_uniform_frames(
    input_path: Path,
    output_dir: Path,
    *,
    max_width: int,
    quality: int,
    frame_count: int,
    cap_at_source: bool = False,
) -> list[Path]:
    """Extract chronologically ordered JPEG frames spanning the full clip.

    By default, FFmpeg's fps filter duplicates frames when ``frame_count``
    exceeds the source frame count, preserving a fixed input shape. When
    ``cap_at_source`` is true, ``frame_count`` is treated as a maximum and all
    source frames are used for shorter clips without padding duplicates.
    """
    if frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")
    source_frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(input_path))
    if seconds <= 0:
        raise ValueError(f"{input_path} has invalid duration {seconds}")
    effective_frame_count = min(frame_count, source_frames) if cap_at_source else frame_count

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = [
        output_dir / f"frame_{index:04d}.jpg"
        for index in range(1, effective_frame_count + 1)
    ]
    if all(path.is_file() for path in expected):
        return expected

    for path in output_dir.glob("frame_*.jpg"):
        path.unlink()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    target_fps = effective_frame_count / seconds
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"fps={target_fps:.12g},trim=end_frame={effective_frame_count},scale={max_width}:-2",
        "-frames:v",
        str(effective_frame_count),
        "-q:v",
        str(quality),
        str(output_dir / "frame_%04d.jpg"),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    missing = [path for path in expected if not path.is_file()]
    if missing:
        raise RuntimeError(
            f"frame extraction produced "
            f"{effective_frame_count - len(missing)}/{effective_frame_count} frames "
            f"for {input_path}"
        )
    return expected


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
    if media_config.get("input_type") == "image_frames":
        frame_config = media_config.get("preprocess", {}).get("frames", {})
        params = {
            "sampler_version": 1,
            "max_width": int(frame_config.get("max_width", 720)),
            "quality": int(frame_config.get("quality", 10)),
            "frame_count": int(frame_config.get("frame_count", 128)),
        }
        if frame_config.get("cap_at_source", False):
            params["cap_at_source"] = True
        transform_params = {
            key: value for key, value in params.items() if key != "sampler_version"
        }
        processed: list[dict[str, Any]] = []
        view_names = [
            str(video.get("camera_view") or Path(video["path"]).stem)
            for video in videos
        ]
        intro = (
            f"The following images are grouped into {len(view_names)} synchronized camera "
            f"views in this order: {', '.join(view_names)}. Within each view, frames are "
            "uniformly sampled across the full execution and ordered chronologically."
        )
        for video in videos:
            source_path = Path(video["path"])
            source_sha = file_sha256(source_path)
            key = _cache_key(source_sha, "image_frames", params)
            output_dir = cache_dir / f"{source_path.stem}.{key}.frames"
            frame_paths = extract_uniform_frames(source_path, output_dir, **transform_params)
            camera_view = str(video.get("camera_view") or source_path.stem)
            actual_frame_count = len(frame_paths)
            for index, frame_path in enumerate(frame_paths, start=1):
                label = None
                if index == 1:
                    label = f"[{camera_view.upper()} VIEW — {actual_frame_count} frames]"
                    if not processed:
                        label = f"{intro}\n\n{label}"
                processed.append(
                    {
                        **video,
                        "source_path": source_path,
                        "path": frame_path,
                        "bytes": frame_path.stat().st_size,
                        "sha256": file_sha256(frame_path),
                        **({"label": label} if label else {}),
                        "api_media": {
                            "preprocessed": True,
                            "source_path": str(source_path),
                            "source_sha256": source_sha,
                            "api_sha256": file_sha256(frame_path),
                            "delivery": "base64_image_url",
                            "fairness_profile": media_config.get("fairness_profile"),
                            "frame_sampling": frame_config,
                            "camera_view": camera_view,
                            "frame_index": index,
                            "actual_frame_count": actual_frame_count,
                        },
                    }
                )
        return processed

    if media_config.get("input_type") == "image_contact_sheet":
        sheet_config = media_config.get("preprocess", {}).get("contact_sheet", {})
        params = {
            "sampler_version": 2,
            "max_width": int(sheet_config.get("max_width", 720)),
            "fps": float(sheet_config.get("fps", 1)),
            "columns": int(sheet_config.get("columns", 4)),
            "rows": int(sheet_config.get("rows", 8)),
            "quality": int(sheet_config.get("quality", 3)),
            "frame_count": (
                int(sheet_config["frame_count"])
                if sheet_config.get("frame_count") is not None else None
            ),
        }
        transform_params = {key: value for key, value in params.items()
                            if key != "sampler_version"}
        processed: list[dict[str, Any]] = []
        for video in videos:
            source_path = Path(video["path"])
            source_sha = file_sha256(source_path)
            key = _cache_key(source_sha, "contact_sheet", params)
            output_path = cache_dir / f"{source_path.stem}.{key}.contact_sheet.jpg"
            if not output_path.is_file():
                create_contact_sheet(source_path, output_path, **transform_params)
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
