"""Import the committed Superset dashboard export into a running Superset.

Native exports mask the database password (``XXXXXXXXXX``) and pin whatever
connection the author used, so they can't be re-imported as-is. This wrapper
rewrites every ``databases/*.yaml`` ``sqlalchemy_uri`` from environment variables
before importing, so the warehouse connection always follows ``.env`` — nothing
is hardcoded and the exported host/user/password are irrelevant.

Runs as a one-shot after the dbt marts exist and Superset is healthy. If no
export ZIP is present it exits 0 (no-op), so it never blocks `docker compose up`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EXPORT_DIR = Path(os.environ.get("DASHBOARD_EXPORT_DIR", "/app/dashboards"))

# Rewrite the sqlalchemy_uri line inside any databases/*.yaml in the export.
_DB_YAML = re.compile(r"/databases/[^/]+\.ya?ml$")
_URI_LINE = re.compile(r"(?m)^(\s*sqlalchemy_uri:).*$")


def warehouse_uri() -> str:
    """Build the warehouse connection from env, falling back to the init.sql
    defaults so it works with no .env and is overridable when one is present."""
    user = os.environ.get("SUPERSET_RO_USER", "superset_ro")
    password = os.environ.get("SUPERSET_RO_PASSWORD", "superset_ro")
    host = os.environ.get("POSTGRES_HOST", "analytics-copilot-db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "analytics_copilot")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def find_export() -> Path | None:
    zips = sorted(EXPORT_DIR.glob("*.zip"))
    return zips[-1] if zips else None


def rewrite(src: Path, dst: Path, uri: str) -> None:
    with (
        zipfile.ZipFile(src) as zin,
        zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if _DB_YAML.search(item.filename):
                text = data.decode("utf-8")
                text, n = _URI_LINE.subn(rf"\1 {uri}", text)
                if n == 0:
                    print(f"  warning: no sqlalchemy_uri in {item.filename}")
                data = text.encode("utf-8")
            zout.writestr(item, data)


def main() -> None:
    export = find_export()
    if export is None:
        print(f"No dashboard export ZIP in {EXPORT_DIR} — nothing to import.")
        return

    uri = warehouse_uri()
    admin = os.environ.get("SUPERSET_ADMIN_USER", "admin")
    safe_target = uri.rsplit("@", 1)[-1]  # host:port/db, no credentials
    print(f"Importing {export.name} → warehouse {safe_target} as '{admin}'...")

    superset = shutil.which("superset") or "superset"
    with tempfile.TemporaryDirectory() as tmp:
        ready = Path(tmp) / "import.zip"
        rewrite(export, ready, uri)
        result = subprocess.run(
            [superset, "import-dashboards", "-p", str(ready), "-u", admin],
        )
    if result.returncode != 0:
        print("Dashboard import failed.", file=sys.stderr)
        sys.exit(result.returncode)
    print("Dashboard import complete.")


if __name__ == "__main__":
    main()
