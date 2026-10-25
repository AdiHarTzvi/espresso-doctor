"""Build the self-contained report.html and slides.html from docs/*.src.html.

Placeholders:
  {{IMG:<file>}}  -> data: URI of evidence/screenshots/<file> (or frontend/public/<file>)
  {{SVG:<name>}}  -> inline contents of docs/diagrams/<name>.svg

Screenshots are downscaled for embedding with macOS `sips` when available; otherwise embedded as-is.
Run from the project root:  .venv/bin/python scripts/build_docs.py
"""
from __future__ import annotations

import base64
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "evidence" / "screenshots"
PUBLIC = ROOT / "frontend" / "public"
DIAGRAMS = ROOT / "docs" / "diagrams"
MAX_WIDTH = 1400
_cache: dict[str, str] = {}


def _image_uri(name: str, tmp: Path) -> str:
    if name in _cache:
        return _cache[name]
    src = SHOTS / name if (SHOTS / name).exists() else PUBLIC / name
    if not src.exists():
        raise FileNotFoundError(f"image not found: {name}")
    data_path = src
    if src.suffix.lower() in {".jpg", ".jpeg", ".png"} and shutil.which("sips"):
        out = tmp / (src.stem + ".jpg")
        subprocess.run(["sips", "-Z", str(MAX_WIDTH), "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        str(src), "--out", str(out)], check=True, capture_output=True)
        data_path = out
    mime = {"svg": "image/svg+xml", "png": "image/png"}.get(data_path.suffix.lower().lstrip("."), "image/jpeg")
    uri = f"data:{mime};base64," + base64.b64encode(data_path.read_bytes()).decode()
    _cache[name] = uri
    return uri


def _svg(name: str) -> str:
    text = (DIAGRAMS / f"{name}.svg").read_text()
    return re.sub(r"<\?xml[^>]*>", "", text).strip()


def build(src_name: str, out_name: str, tmp: Path) -> None:
    html = (ROOT / "docs" / src_name).read_text()
    html = re.sub(r"\{\{IMG:([^}]+)\}\}", lambda m: _image_uri(m.group(1).strip(), tmp), html)
    html = re.sub(r"\{\{SVG:([^}]+)\}\}", lambda m: _svg(m.group(1).strip()), html)
    leftover = re.findall(r"\{\{[A-Z]+:[^}]+\}\}", html)
    if leftover:
        raise SystemExit(f"unresolved placeholders in {src_name}: {leftover}")
    (ROOT / out_name).write_text(html)
    print(f"wrote {out_name} ({len(html) / 1e6:.2f} MB)")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as t:
        for src, out in (("report.src.html", "report.html"), ("slides.src.html", "slides.html")):
            if (ROOT / "docs" / src).exists():
                build(src, out, Path(t))
