from __future__ import annotations

import pathlib
from typing import Any

import yaml  # type: ignore[import-untyped]


def load_prompt(prompts_dir: pathlib.Path, name: str) -> dict[str, str]:
    """Load a prompt template from prompts/{name}.yaml.

    Returns a dict with at least 'system' and 'user' keys.
    """
    path = prompts_dir / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f)
    return {str(k): str(v) for k, v in raw.items()}
