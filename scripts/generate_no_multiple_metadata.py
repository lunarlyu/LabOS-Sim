"""Generate metadata with ambiguous `multiple` condition samples removed."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def has_multiple_marker(sample: dict) -> bool:
    fields = [
        sample.get("condition_folder", ""),
        sample.get("condition_description", ""),
        sample.get("relative_path", ""),
        sample.get("scenario_name", ""),
    ]
    fields.extend(sample.get("failure_modes") or [])
    fields.extend(sample.get("scenario_tags") or [])
    return any("multiple" in str(field).lower() for field in fields)


def main() -> None:
    source = Path("metadata/real_human_samples.json")
    output = Path("metadata/real_human_samples_no_multiple.json")
    metadata = json.loads(source.read_text(encoding="utf-8"))
    original_samples = metadata["samples"]
    kept_samples = [sample for sample in original_samples if not has_multiple_marker(sample)]
    removed_samples = [sample["sample_id"] for sample in original_samples if has_multiple_marker(sample)]

    metadata["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["generator"] = "scripts/generate_no_multiple_metadata.py"
    metadata["source_metadata_path"] = str(source)
    metadata["filter"] = {
        "description": "Removed samples whose condition, path, tags, or failure modes contain `multiple`.",
        "removed_count": len(removed_samples),
        "removed_sample_ids": removed_samples,
    }
    metadata["summary"] = dict(metadata.get("summary") or {})
    metadata["summary"]["num_samples"] = len(kept_samples)
    metadata["summary"]["removed_multiple_samples"] = len(removed_samples)
    metadata["samples"] = kept_samples

    output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(kept_samples)} samples; removed {len(removed_samples)}.")
    for sample_id in removed_samples:
        print(f"removed: {sample_id}")


if __name__ == "__main__":
    main()
