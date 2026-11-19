import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from git_retro.core import compute, find_repos, read_commits, resolve_identity
from git_retro.demo import demo_commits
from git_retro.render import render


def commit(repo, files, msg, when, email="eu@x.dev", name="Eu"):
    for path, content in files.items():
        p = repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_NAME": name,
           "GIT_COMMITTER_EMAIL": email, "GIT_COMMITTER_NAME": name}
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", msg], cwd=repo, check=True, env=env)


class GitRetroTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "app"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        commit(self.repo, {"a.py": "x = 1\n" * 10}, "feat: começo", "2026-03-02T10:00:00-03:00")
        commit(self.repo, {"a.py": "x = 2\n" * 12}, "fix: conserta x", "2026-03-03T10:30:00-03:00")
        commit(self.repo, {"b.js": "let y\n" * 5}, "feat: tela nova", "2026-03-04T02:15:00-03:00", email="outro@trabalho.com", name="Eu")
        commit(self.repo, {".venv/lib/pkg.py": "z\n" * 900}, "oops venv", "2026-03-05T15:00:00-03:00")
        commit(self.repo, {"c.py": "w\n"}, "alguém", "2026-03-05T16:00:00-03:00", email="colega@x.dev", name="Colega")
        commit(self.repo, {"old.py": "v\n"}, "ano passado", "2025-06-01T12:00:00-03:00")
        (self.root / "node_modules" / "lib").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.root / "node_modules" / "lib", check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def data(self):
        cs = read_commits(self.repo, 2026)
        emails, names = resolve_identity(cs, {"eu@x.dev"})
        mine = [c for c in cs if c.email in emails or c.name.lower() in names]
        return compute(mine, 2026, name="Eu"), emails

    def test_finds_repos_but_skips_dependency_folders(self):
        self.assertEqual(find_repos([self.root]), [self.repo.resolve()])

    def test_only_this_year_and_merges_identities(self):
        d, emails = self.data()
        self.assertEqual(emails, {"eu@x.dev", "outro@trabalho.com"})
        self.assertEqual(d["totals"]["commits"], 4)          # sem o colega e sem 2025
        self.assertEqual(d["totals"]["active_days"], 4)
        self.assertEqual(d["streak"]["length"], 4)

    def test_vendor_lines_are_left_out(self):
        d, _ = self.data()
        self.assertEqual(d["ignored"]["lines"], 900)
        self.assertEqual(d["totals"]["added"], 10 + 12 + 5)
        self.assertEqual(d["totals"]["removed"], 10)
        self.assertEqual(d["langs"][0]["name"], "Python")

    def test_night_commit_and_fix_share(self):
        d, _ = self.data()
        self.assertEqual(d["night"]["time"], "02:15")
        self.assertEqual(d["fix_pct"], 25)

    def test_hide_messages_and_anonymize(self):
        cs = read_commits(self.repo, 2026)
        d = compute(cs, 2026, show_messages=False, anonymize=True)
        self.assertEqual(d["night"]["message"], "")
        self.assertEqual(d["words"], [])
        self.assertTrue(all(r["name"].startswith("projeto-") for r in d["repos"]))

    def test_render_is_self_contained_and_escapes(self):
        d = compute(demo_commits(2026), 2026, name="</script><b>x")
        d["lang"] = "en"
        html = render(d)
        self.assertNotIn("</script><b>", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))
        self.assertIn('"year": 2026', html)


if __name__ == "__main__":
    unittest.main()
