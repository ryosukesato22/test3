from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = ROOT / ".web_build" / "twin_drop_duel"
WEB_DIR = ROOT / "web"
TMP_APP = ROOT / "twin_drop_duel.pyxapp"
TMP_HTML = ROOT / "twin_drop_duel.html"


def run_pyxel(*args: str) -> None:
    command = [sys.executable, "-m", "pyxel", *args]
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    shutil.rmtree(TMP_DIR.parent, ignore_errors=True)
    shutil.rmtree(WEB_DIR, ignore_errors=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(ROOT / "main.py", TMP_DIR / "main.py")

    run_pyxel("package", str(TMP_DIR), str(TMP_DIR / "main.py"))
    run_pyxel("app2html", str(TMP_APP))

    shutil.move(str(TMP_HTML), str(WEB_DIR / "index.html"))
    (WEB_DIR / ".nojekyll").write_text("", encoding="utf-8")

    if TMP_APP.exists():
        TMP_APP.unlink()
    shutil.rmtree(TMP_DIR.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
