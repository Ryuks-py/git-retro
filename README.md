# git retro

**Your year in git, as an animated story you can share.** One command reads the repositories on your machine (private ones included) and turns your commits into a Wrapped-style page: your busiest day, your longest streak, the hour you code the most, your languages, your latest-night commit and the lines you committed but never wrote.

It runs **100% locally**. No account, no token, no upload. Your code never leaves your computer.

![Slides from a demo year](docs/preview.png)

**[See the live demo →](https://ryuks-py.github.io/git-retro/)** · [em português](https://ryuks-py.github.io/git-retro/pt.html)

## Quick start

```bash
pipx install git+https://github.com/Ryuks-py/git-retro
git-retro ~/code
```

That's it: it finds every repository under `~/code`, keeps only your commits from this year and opens the page in your browser. Or try it without installing:

```bash
git clone https://github.com/Ryuks-py/git-retro && cd git-retro
python3 -m git_retro ~/code
```

Python 3.9+ and `git`. No other dependencies.

## What's inside

| Slide | What it shows |
|---|---|
| Commits | total, repositories, active days, average per day |
| Lines | written vs. deleted |
| Your year, day by day | a calendar heatmap and your busiest day |
| Streak | most days in a row with at least one commit |
| Your clock | a 24-hour radial chart and your peak hour |
| Your weekday | which day you commit the most |
| You are… | a persona: *Night owl*, *Weekend warrior*, *Early bird*, *Night shift* or *Office hours* |
| Latest commit | the commit closest to dawn, with its message |
| Confession | lines from `venv/`, `node_modules/`, build output and huge imports you committed (left out of every other number) |
| Languages | share of changed lines per language |
| Repositories | where you spent your time |
| Words of the year | the words you used most in commit messages, and how many commits were fixes |
| Biggest commit | the largest change you made in one go |
| First to last | your first and last commit of the year |
| Summary | everything on one card, with a **Download image** button (1080×1920, ready for stories) |

Navigate with **← →**, tap the sides, or swipe. Space pauses; press and hold also pauses.

## You have more than one e-mail? It figures that out

Most people commit with a personal e-mail, a work e-mail and whatever their laptop had configured. git retro starts from the `user.email` in your git config and joins every e-mail that was used with the same author name. If it still can't find you, it lists who it saw so you can say which one is you:

```bash
git-retro ~/code --author me@personal.dev --author me@company.com
```

## Options

```
git-retro [paths ...]        folders to scan (default: current folder)
  -y, --year 2025            another year (default: this year; last year during January)
  -a, --author EMAIL|NAME    your identity, repeatable
  --name "Ana"               name on the first slide
  --lang pt|en               page language (default: from your system)
  --no-messages              hide commit messages from the page
  --anonymize                show repositories as projeto-A, projeto-B…
  -o, --output FILE          output file (default: git-retro-YEAR.html)
  --depth 4                  how deep to look for repositories
  --demo                     a made-up year, to see it without your data
  --no-open                  don't open the browser
```

Sharing the page from work? `--no-messages --anonymize` keeps the stats and drops anything that could identify a client or project.

## How the numbers are counted

- Only commits **authored** in the chosen year, by you, across all branches, without merge commits. The same commit in two clones counts once.
- Lines ignore dependency and build folders (`node_modules`, `venv*`, `site-packages`, `vendor`, `dist`, `build`, migrations…), lock files, minified files, images and fonts.
- A single file with more than 5,000 changed lines, a data file (JSON, CSV, SQL…) with more than 1,500, or a whole commit with more than 30,000 is treated as generated or imported. Those lines go to the *Confession* slide instead.

## Privacy

The output is a single HTML file with the numbers inside. It loads no fonts, scripts or images from anywhere, so it works offline and makes no network requests. What ends up in it: aggregate stats, repository names and a few commit messages (latest, biggest, first and last). Use `--no-messages` and `--anonymize` to remove them.

## Development

```bash
python3 -m unittest discover -s tests -t .
python3 -m git_retro --demo        # regenerate with fake data
```

## License

MIT

---

<details>
<summary><b>Em português</b></summary>

**A sua retrospectiva do ano no git, em formato de stories.** Um comando lê os repositórios do seu computador (inclusive os privados) e gera uma página animada: dia mais intenso, maior sequência, horário em que você mais programa, linguagens, o commit mais tarde da noite e as linhas que você commitou sem ter escrito.

Roda **100% local**: sem conta, sem token, sem upload.

```bash
pipx install git+https://github.com/Ryuks-py/git-retro
git-retro ~/projetos
```

A página sai em português se o seu sistema estiver em português (ou use `--lang pt`). Usa mais de um e-mail nos commits? Ele junta sozinho os e-mails que aparecem com o mesmo nome; se precisar, passe `--author` quantas vezes quiser. Para compartilhar sem expor cliente nem projeto: `--no-messages --anonymize`.

</details>
