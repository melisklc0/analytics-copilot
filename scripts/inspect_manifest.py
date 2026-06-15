"""Inspect parsed AI mart models from a dbt manifest.json.

Usage:
    uv run python scripts/inspect_manifest.py
    uv run python scripts/inspect_manifest.py --path dbt/target/manifest.json
    uv run python scripts/inspect_manifest.py --model mart_customers
    uv run python scripts/inspect_manifest.py --model mart_customers --context
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analytics_copilot.services.manifest_parser import ManifestParser

DEFAULT_MANIFEST = Path("dbt/target/manifest.json")
FALLBACK_MANIFEST = Path("tests/fixtures/manifest_sample.json")

# Logs go to stderr only — stdout stays clean for Markdown output
logging.basicConfig(
    level=logging.INFO, stream=sys.stderr, format="%(levelname)s  %(message)s"
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--path", type=Path, default=None, help="Path to manifest.json")
    p.add_argument("--model", default=None, help="Show details for a specific model")
    p.add_argument(
        "--context",
        action="store_true",
        help="Print the LLM context block for the model",
    )
    return p


def print_summary(parser: ManifestParser) -> None:
    models = parser.get_all_models()
    print(f"# AI Mart Models ({len(models)} loaded)\n")
    print("| model | relation | columns | filterable |")
    print("|---|---|---|---|")
    for m in models:
        filterable = ", ".join(f"`{c.name}`" for c in m.columns if c.filterable) or "—"
        print(f"| `{m.name}` | `{m.relation}` | {len(m.columns)} | {filterable} |")
    print("\nTip: `--model <name> --context` to see the LLM context block.")


def print_detail(parser: ManifestParser, model_name: str, show_context: bool) -> None:
    model = parser.models.get(model_name)
    if not model:
        available = sorted(parser.models.keys())
        print(
            f"Model '{model_name}' not found.\nAvailable: {available}", file=sys.stderr
        )
        sys.exit(1)

    print(f"# {model.name}\n")
    print(f"**Table:** `{model.relation}`\n")
    print(f"{model.description}\n")
    print("| column | type | filterable | description |")
    print("|---|---|---|---|")
    for col in model.columns:
        flag = "yes" if col.filterable else ""
        desc = col.description.replace("|", "\\|")
        print(f"| `{col.name}` | `{col.data_type}` | {flag} | {desc} |")

    if show_context:
        print("\n---\n\n## LLM context block\n")
        print(parser.get_context([model_name]))


def main() -> None:
    args = build_parser().parse_args()

    if args.path:
        manifest_path = args.path
    elif DEFAULT_MANIFEST.exists():
        manifest_path = DEFAULT_MANIFEST
    else:
        print("dbt/target/manifest.json not found — using fixture", file=sys.stderr)
        manifest_path = FALLBACK_MANIFEST

    manifest_parser = ManifestParser(manifest_path)

    if args.model:
        print_detail(manifest_parser, args.model, args.context)
    else:
        print_summary(manifest_parser)


if __name__ == "__main__":
    main()
