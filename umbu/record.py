"""The campaign record: one JSON file per run that every pipeline step reads and adds to."""
import json
from pathlib import Path

from umbu.context import RUNS_DIR


def _stopped(run_dir: Path) -> bool:
    return json.loads((run_dir / "record.json").read_text(encoding="utf-8")).get("status") == "needs_input"


def latest_run_dir() -> Path:
    # Scenario copies are named <run>-<scenario>; skip them so we always get the agents' own run.
    # Also skip runs the Planner stopped on (brief needed a decision): nothing was created.
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir() and p.name.count("-") == 1
                  and (p / "record.json").exists() and not _stopped(p))
    if not runs:
        raise SystemExit("No runs found. Run `python run_planner.py` first.")
    return runs[-1]


def load_record(run_dir: Path) -> dict:
    return json.loads((run_dir / "record.json").read_text(encoding="utf-8"))


def save_record(run_dir: Path, record: dict) -> None:
    (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
