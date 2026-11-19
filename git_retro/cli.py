"""git retro: a sua retrospectiva do ano no git, gerada localmente."""
from __future__ import annotations

import argparse
import locale
import os
import sys
import webbrowser
from datetime import date
from pathlib import Path

from . import __version__
from .core import compute, config_emails, find_repos, read_commits, resolve_identity, top_authors
from .render import render


def _default_lang():
    for v in (os.environ.get("LC_ALL"), os.environ.get("LANG"), (locale.getlocale()[0] or "")):
        if v:
            return "pt" if v.lower().startswith("pt") else "en"
    return "en"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="git-retro", description="Your year in git, as an animated story page. Runs 100%% locally.")
    ap.add_argument("paths", nargs="*", default=["."], help="folders to scan for git repositories (default: current folder)")
    ap.add_argument("-y", "--year", type=int, default=None, help="year to look at (default: this year, or last year in January)")
    ap.add_argument("-a", "--author", action="append", default=[], help="your e-mail or name; repeat for each identity you use")
    ap.add_argument("-o", "--output", default=None, help="output HTML file (default: git-retro-YEAR.html)")
    ap.add_argument("--name", default=None, help="name shown on the page (default: your git user.name)")
    ap.add_argument("--lang", choices=["pt", "en"], default=None, help="page language (default: from your system)")
    ap.add_argument("--no-messages", action="store_true", help="hide commit messages from the page")
    ap.add_argument("--anonymize", action="store_true", help="replace repository names with projeto-A, projeto-B…")
    ap.add_argument("--depth", type=int, default=4, help="how deep to look for repositories (default: 4)")
    ap.add_argument("--demo", action="store_true", help="use a made-up year instead of your repositories")
    ap.add_argument("--no-open", action="store_true", help="do not open the page in the browser")
    ap.add_argument("--version", action="version", version=f"git-retro {__version__}")
    a = ap.parse_args(argv)

    today = date.today()
    year = a.year or (today.year - 1 if today.month == 1 else today.year)
    lang = a.lang or _default_lang()
    say = (lambda pt, en: print(pt if lang == "pt" else en, file=sys.stderr))

    if a.demo:
        from .demo import demo_commits
        mine = demo_commits(year, lang=lang)
        name = a.name or ("Você" if lang == "pt" else "You")
    else:
        repos = find_repos(a.paths, a.depth)
        if not repos:
            say("Nenhum repositório git encontrado aqui. Passe a pasta onde ficam seus projetos: git-retro ~/projetos",
                "No git repositories found here. Point it at your projects folder: git-retro ~/code")
            return 1
        say(f"→ {len(repos)} repositórios encontrados, lendo commits de {year}…",
            f"→ found {len(repos)} repositories, reading {year} commits…")
        commits = [c for r in repos for c in read_commits(r, year)]
        if not commits:
            say(f"Nenhum commit em {year} nesses repositórios.", f"No commits in {year} in those repositories.")
            return 1
        seeds = {x for x in a.author if "@" in x} or config_emails(repos)
        names = {x for x in a.author if "@" not in x}
        if not seeds and not names:
            (email, nm), _ = top_authors(commits, 1)[0]
            seeds = {email}
            say(f"  (sem user.email configurado; usando quem mais commitou: {nm} <{email}>)",
                f"  (no user.email configured; using the top committer: {nm} <{email}>)")
        emails, names = resolve_identity(commits, seeds, names)
        mine = [c for c in commits if c.email in emails or c.name.lower() in names]
        say(f"  você = {', '.join(sorted(emails))}", f"  you = {', '.join(sorted(emails))}")
        if not mine:
            say("Nenhum commit seu encontrado. Quem aparece nesses repositórios:",
                "None of the commits are yours. Who shows up in these repositories:")
            for (email, nm), n in top_authors(commits):
                print(f"    {n:5}  {nm} <{email}>", file=sys.stderr)
            say("Rode de novo com --author seu@email (pode repetir).", "Run again with --author you@email (repeatable).")
            return 1
        name = a.name or (mine[-1].name.split()[0] if mine[-1].name else "")

    data = compute(mine, year, show_messages=not a.no_messages, anonymize=a.anonymize, name=name)
    data["lang"] = lang
    out = Path(a.output or f"git-retro-{year}.html")
    out.write_text(render(data), encoding="utf-8")
    t = data["totals"]
    say(f"✓ {t['commits']} commits em {t['repos']} repositórios → {out}",
        f"✓ {t['commits']} commits across {t['repos']} repositories → {out}")
    if not a.no_open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
