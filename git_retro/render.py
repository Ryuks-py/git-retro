"""Coloca os números e as fontes dentro da página (um HTML só, sem nada externo)."""
import base64
import json
from importlib.resources import files

FONTS = ("display-800", "text-500", "mono-600")


def render(data: dict) -> str:
    pkg = files("git_retro")
    tpl = pkg.joinpath("template.html").read_text(encoding="utf-8")
    for f in FONTS:
        b64 = base64.b64encode(pkg.joinpath("fonts", f + ".woff2").read_bytes()).decode()
        tpl = tpl.replace(f"/*FONT:{f}*/", b64, 1)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("/*DATA*/null", blob, 1)
