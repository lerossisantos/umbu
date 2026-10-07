"""The campaign record: one JSON file per run that every pipeline step reads and adds to."""
import json
from pathlib import Path

from umbu.context import RUNS_DIR


def latest_run_dir() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise SystemExit("No runs found. Run `python run_planner.py` first.")
    return runs[-1]


def load_record(run_dir: Path) -> dict:
    return json.loads((run_dir / "record.json").read_text(encoding="utf-8"))


def save_record(run_dir: Path, record: dict) -> None:
    (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
