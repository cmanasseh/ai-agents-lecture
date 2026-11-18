"""Every run is traced: one JSON line per run, one file per version."""

import json
from pathlib import Path

RUNS_DIR = Path("runs")


def write_trace(runs_dir: Path, record: dict) -> None:
    """Append `record` to `<runs_dir>/<version>.jsonl`."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    with (runs_dir / f"{record['version']}.jsonl").open("a") as f:
        f.write(json.dumps(record) + "\n")
