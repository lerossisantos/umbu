"""Loads the Northwind context files and agent prompts from disk."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = ROOT / "context"
PROMPTS_DIR = ROOT / "prompts"
RUNS_DIR = ROOT / "runs"


def load_context(*names: str) -> str:
    """Wrap each context file in a tag so the model knows where each rule came from."""
    parts = []
    for name in names:
        text = (CONTEXT_DIR / name).read_text(encoding="utf-8")
        parts.append(f'<context file="{name}">\n{text}\n</context>')
    return "\n\n".join(parts)


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")
