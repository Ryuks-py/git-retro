"""Coloca os números dentro da página (um HTML só, sem nada externo)."""
import json
from importlib.resources import files


def render(data: dict) -> str:
    tpl = files("git_retro").joinpath("template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("/*DATA*/null", blob, 1)
