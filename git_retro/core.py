"""Coleta de commits nos repositórios locais e cálculo das estatísticas do ano.

Tudo roda localmente com o próprio `git`; nada é enviado para fora.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

SKIP_DIRS = {"node_modules", ".venv", "venv", "env", ".tox", "__pycache__", "dist", "build",
             ".next", ".cache", "vendor", "target", ".gradle", ".dart_tool", "Pods"}

# pastas de dependência e de build: ninguém escreveu aquilo (mas alguém commitou)
VENDOR = re.compile(r"(^|/)(node_modules|bower_components|site-packages|\.?venv[^/]*|virtualenv|env|\.tox|vendor|Pods|"
                    r"\.dart_tool|staticfiles|collected_static|dist|build|out|target|coverage|htmlcov|\.next|\.nuxt|__pycache__|migrations|drizzle/meta)/")
# arquivos que inflam a contagem de linhas sem ninguém ter escrito nada
NOISE = re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|uv\.lock|"
                   r"composer\.lock|Cargo\.lock|Gemfile\.lock|pubspec\.lock|go\.sum)$|"
                   r"\.min\.(js|css)$|\.map$|\.(svg|png|jpe?g|gif|webp|ico|pdf|zip|gz|woff2?|ttf|otf|mp4|mp3|lock|pyc)$")
DATA_EXT = re.compile(r"\.(json|csv|tsv|xml|sql|txt|ya?ml|geojson|ndjson)$", re.I)
GENERATED_LINES = 5000   # um arquivo só com mais que isso num commit é gerado/importado
DATA_LINES = 1500        # idem para arquivos de dados
IMPORT_LINES = 30000     # um commit inteiro maior que isso é código trazido de outro lugar

LANGS = {
    "py": ("Python", "#3B82F6"), "js": ("JavaScript", "#F7DF1E"), "mjs": ("JavaScript", "#F7DF1E"),
    "jsx": ("JavaScript", "#F7DF1E"), "ts": ("TypeScript", "#3178C6"), "tsx": ("TypeScript", "#3178C6"),
    "html": ("HTML", "#E34F26"), "htm": ("HTML", "#E34F26"), "css": ("CSS", "#A855F7"),
    "scss": ("CSS", "#A855F7"), "sass": ("CSS", "#A855F7"), "dart": ("Dart", "#00B4AB"),
    "kt": ("Kotlin", "#A97BFF"), "kts": ("Kotlin", "#A97BFF"), "java": ("Java", "#F89820"),
    "go": ("Go", "#00ADD8"), "rs": ("Rust", "#DEA584"), "rb": ("Ruby", "#CC342D"), "php": ("PHP", "#777BB4"),
    "c": ("C", "#A8B9CC"), "h": ("C", "#A8B9CC"), "cpp": ("C++", "#F34B7D"), "cc": ("C++", "#F34B7D"),
    "hpp": ("C++", "#F34B7D"), "cs": ("C#", "#68217A"), "swift": ("Swift", "#F05138"),
    "sql": ("SQL", "#E38C00"), "sh": ("Shell", "#89E051"), "bash": ("Shell", "#89E051"),
    "vue": ("Vue", "#41B883"), "svelte": ("Svelte", "#FF3E00"), "lua": ("Lua", "#000080"),
    "md": ("Markdown", "#9CA3AF"), "json": ("JSON", "#6B7280"), "yml": ("YAML", "#CB171E"),
    "yaml": ("YAML", "#CB171E"), "toml": ("TOML", "#9C4221"), "ex": ("Elixir", "#6E4A7E"),
    "exs": ("Elixir", "#6E4A7E"), "scala": ("Scala", "#DC322F"), "r": ("R", "#198CE7"),
    "ipynb": ("Jupyter", "#F37626"), "tf": ("Terraform", "#7B42BC"), "zig": ("Zig", "#F7A41D"),
}
SPECIAL_FILES = {"Dockerfile": ("Docker", "#2496ED"), "Makefile": ("Make", "#427819")}

STOP = set("""a o e é de da do das dos em no na nos nas um uma para pra por com sem que se ao à
as os mais e ou the a an and or to of in on for with from by at is it this that be as into
não nao sim mais fix fixes fixed feat chore refactor docs style test tests wip merge update updates updated add
added adds remove removed""".split())

_SEP = "\x1e"
_FS = "\x1f"


@dataclass
class Commit:
    hash: str
    email: str
    name: str
    when: datetime
    subject: str
    repo: str
    files: list = field(default_factory=list)   # (added, removed, path)


def find_repos(roots, max_depth=4):
    """Acha pastas com .git dentro das raízes dadas, sem descer em node_modules e afins."""
    found = []
    for root in roots:
        root = Path(root).expanduser().resolve()
        if (root / ".git").exists():
            found.append(root)
        base = len(root.parts)
        for cur, dirs, _ in os.walk(root):
            depth = len(Path(cur).parts) - base
            if depth >= max_depth:
                dirs[:] = []
                continue
            keep = []
            for d in dirs:
                if d in SKIP_DIRS or d.startswith(".") and d != ".git":
                    continue
                p = Path(cur) / d
                if d == ".git":
                    continue
                if (p / ".git").exists():
                    found.append(p)
                keep.append(d)
            dirs[:] = keep
    seen, out = set(), []
    for r in found:
        if r not in seen:
            seen.add(r); out.append(r)
    return out


def _git(repo, *args, stdin=None):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", input=stdin)
    return r.stdout if r.returncode == 0 else ""


def config_emails(repos):
    """E-mails configurados (global e em cada repositório): ponto de partida para achar 'você'."""
    emails = set()
    g = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()
    if g:
        emails.add(g.lower())
    for r in repos:
        e = _git(r, "config", "--local", "user.email").strip()
        if e:
            emails.add(e.lower())
    return emails


def read_commits(repo, year):
    # 1) lista leve de datas; `--since` não serve: ele para no primeiro commit antigo do caminho
    #    (rebase, data alterada) e some com o resto do ano
    hashes = [h for h, _, d in (l.partition(" ") for l in _git(repo, "log", "--all", "--no-merges", "--format=%H %aI").splitlines())
              if d[:4] == str(year)]
    if not hashes:
        return []
    # 2) detalhes só dos commits do ano
    fmt = f"--pretty=format:{_SEP}%H{_FS}%ae{_FS}%an{_FS}%aI{_FS}%s"
    out = _git(repo, "log", "--no-walk=unsorted", "--stdin", "--numstat", fmt, stdin="\n".join(hashes) + "\n")
    commits = []
    for block in out.split(_SEP):
        if not block.strip():
            continue
        head, _, rest = block.partition("\n")
        parts = head.split(_FS)
        if len(parts) < 5:
            continue
        h, email, name, iso, subject = parts[:5]
        try:
            when = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.year != year:
            continue
        c = Commit(h, email.lower(), name, when, subject.strip(), repo.name)
        for line in rest.splitlines():
            bits = line.split("\t")
            if len(bits) != 3:
                continue
            a, d, path = bits
            if " => " in path:  # renomeado: fica o destino
                path = re.sub(r"\{[^{}]* => ([^{}]*)\}", r"\1", path).split(" => ")[-1]
            c.files.append((int(a) if a.isdigit() else 0, int(d) if d.isdigit() else 0, path))
        commits.append(c)
    return commits


def resolve_identity(commits, seeds, names=()):
    """Junta os e-mails da mesma pessoa: quem usa um nome que algum e-mail-semente usa também é você."""
    emails = {e.lower() for e in seeds}
    names = {n.lower() for n in names}
    for _ in range(3):
        for c in commits:
            if c.email in emails:
                names.add(c.name.lower())
        for c in commits:
            if c.name.lower() in names:
                emails.add(c.email)
    return emails, names


def top_authors(commits, n=8):
    return Counter((c.email, c.name) for c in commits).most_common(n)


def lang_of(path):
    base = path.rsplit("/", 1)[-1]
    if base in SPECIAL_FILES:
        return SPECIAL_FILES[base]
    if "." not in base:
        return None
    return LANGS.get(base.rsplit(".", 1)[-1].lower())


def _night_rank(dt):
    """Quanto mais perto das 5h, mais 'madrugada' é (0h=24, 4h59=28,99)."""
    h = dt.hour + dt.minute / 60
    return h + 24 if h < 5 else (h if h >= 22 else -1)


def compute(commits, year, *, show_messages=True, anonymize=False, name=""):
    commits = sorted({c.hash: c for c in commits}.values(), key=lambda c: c.when)
    if not commits:
        return None

    repo_alias = {}
    def rname(r):
        if not anonymize:
            return r
        if r not in repo_alias:
            repo_alias[r] = f"projeto-{chr(65 + len(repo_alias) % 26)}"
        return repo_alias[r]
    msg = (lambda s: s) if show_messages else (lambda s: "")

    days = Counter(c.when.date().isoformat() for c in commits)
    hours = [0] * 24
    weekdays = [0] * 7
    months = [0] * 12
    lang_lines = Counter()
    lang_color = {}
    per_repo = defaultdict(lambda: {"commits": 0, "added": 0, "removed": 0})
    added = removed = 0
    files = set()
    ignored = 0
    ignored_dirs = Counter()
    words = Counter()
    types = Counter()
    biggest = None

    for c in commits:
        hours[c.when.hour] += 1
        weekdays[c.when.weekday()] += 1
        months[c.when.month - 1] += 1
        pr = per_repo[c.repo]
        pr["commits"] += 1
        size = 0
        csize = sum(a + d for a, d, path in c.files if not NOISE.search(path) and not VENDOR.search(path))
        if csize > IMPORT_LINES:
            ignored += csize
            ignored_dirs[f"{c.subject[:40]}"] += csize
            continue
        for a, d, path in c.files:
            if NOISE.search(path):
                continue
            vm = VENDOR.search(path)
            if vm or a + d > GENERATED_LINES or (DATA_EXT.search(path) and a + d > DATA_LINES):
                ignored += a + d
                ignored_dirs[path[:vm.end()] if vm else path] += a + d
                continue
            files.add((c.repo, path))
            added += a; removed += d; size += a + d
            pr["added"] += a; pr["removed"] += d
            lg = lang_of(path)
            if lg:
                lang_lines[lg[0]] += a + d
                lang_color[lg[0]] = lg[1]
        if biggest is None or size > biggest[0]:
            biggest = (size, c)
        m = re.match(r"^(\w+)(\([^)]*\))?!?:", c.subject)
        if m:
            types[m.group(1).lower()] += 1
        elif re.match(r"(?i)^(fix|corrig|conserta|ajust)", c.subject):
            types["fix"] += 1
        for w in re.findall(r"[a-zà-ú]{3,}", c.subject.lower()):
            if w not in STOP:
                words[w] += 1

    # sequência de dias seguidos
    ds = sorted(date.fromisoformat(d) for d in days)
    best = (1, ds[0], ds[0]); run_start = ds[0]
    for prev, cur in zip(ds, ds[1:]):
        if cur - prev != timedelta(days=1):
            run_start = cur
        ln = (cur - run_start).days + 1
        if ln > best[0]:
            best = (ln, run_start, cur)

    busiest_day, busiest_n = max(days.items(), key=lambda kv: (kv[1], kv[0]))
    night = max(commits, key=lambda c: _night_rank(c.when))
    night = night if _night_rank(night.when) > 0 else None

    total = len(commits)
    late = sum(hours[0:5]); evening = sum(hours[18:24]); early = sum(hours[5:9])
    weekend = weekdays[5] + weekdays[6]
    if late / total >= .12:
        persona = "owl"
    elif weekend / total >= .3:
        persona = "weekend"
    elif early / total >= .25:
        persona = "early"
    elif evening / total >= .35:
        persona = "night"
    else:
        persona = "office"

    ignored_top = None
    if ignored_dirs:
        top_path = ignored_dirs.most_common(1)[0][0]
        repo = next((c.repo for c in commits for f in c.files if f[2].startswith(top_path)), None) \
            or next((c.repo for c in commits if c.subject.startswith(top_path)), "")
        ignored_top = (repo, top_path)
    tot_lang = sum(lang_lines.values()) or 1
    langs = [{"name": n, "lines": v, "pct": round(v * 100 / tot_lang, 1), "color": lang_color[n]}
             for n, v in lang_lines.most_common(6)]
    repos = sorted(({"name": rname(r), **v} for r, v in per_repo.items()), key=lambda x: -x["commits"])[:6]
    first, last = commits[0], commits[-1]

    return {
        "year": year,
        "name": name,
        "totals": {"commits": total, "repos": len(per_repo), "active_days": len(days),
                   "added": added, "removed": removed, "files": len(files)},
        "days": dict(days),
        "hours": hours, "weekdays": weekdays, "months": months,
        "langs": langs, "repos": repos,
        "streak": {"length": best[0], "start": best[1].isoformat(), "end": best[2].isoformat()},
        "busiest": {"date": busiest_day, "commits": busiest_n},
        "night": night and {"time": night.when.strftime("%H:%M"), "date": night.when.date().isoformat(),
                            "message": msg(night.subject), "repo": rname(night.repo)},
        "biggest": biggest and biggest[0] and {"lines": biggest[0], "message": msg(biggest[1].subject),
                                               "repo": rname(biggest[1].repo), "date": biggest[1].when.date().isoformat()},
        "first": {"date": first.when.date().isoformat(), "message": msg(first.subject), "repo": rname(first.repo)},
        "last": {"date": last.when.date().isoformat(), "message": msg(last.subject), "repo": rname(last.repo)},
        "words": words.most_common(8) if show_messages else [],
        "ignored": {"lines": ignored, "top": (rname(ignored_top[0]) + " · " + ignored_top[1]) if ignored_top else ""},
        "fix_pct": round(types.get("fix", 0) * 100 / total),
        "persona": persona,
        "weekend_pct": round(weekend * 100 / total),
    }
