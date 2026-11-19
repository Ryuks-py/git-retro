"""Um ano inventado, para ver a retrospectiva sem apontar para repositório nenhum."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from .core import Commit

REPOS = ["api-pagamentos", "app-entregas", "painel-admin", "site-institucional", "dotfiles", "cli-deploy"]
FILES = {
    "api-pagamentos": ["app/models.py", "app/views.py", "app/services/pix.py", "tests/test_pix.py", "app/schema.sql"],
    "app-entregas": ["lib/main.dart", "lib/screens/mapa.dart", "lib/api.dart", "android/app/build.gradle.kts"],
    "painel-admin": ["src/App.tsx", "src/pages/Pedidos.tsx", "src/api.ts", "src/styles.css"],
    "site-institucional": ["index.html", "css/site.css", "js/menu.js"],
    "dotfiles": ["install.sh", ".zshrc.sh", "README.md"],
    "cli-deploy": ["cmd/root.go", "internal/ssh.go", "Dockerfile", "README.md"],
}
MSGS = [
    "feat: pagamento por pix com QR dinâmico", "fix: timezone no relatório mensal", "ajusta layout do checkout no celular",
    "feat: tela de mapa com rota do entregador", "corrige cálculo de frete", "refactor: separa serviço de cobrança",
    "fix: botão salvar duplicava pedido", "feat: exportar pedidos em csv", "deploy automático na main",
    "testes do webhook do banco", "fix: fix do fix", "melhora performance da listagem", "feat: modo escuro",
    "corrige migração quebrada", "atualiza dependências", "feat: login com código por e-mail", "por que isso funcionava antes",
    "fix: cache do dashboard", "feat: filtros na tela de pedidos", "remove código morto",
]
MSGS_EN = [
    "feat: pix-style instant payments with dynamic QR", "fix: timezone in monthly report", "tweak checkout layout on mobile",
    "feat: live map with courier route", "fix shipping cost rounding", "refactor: split billing service",
    "fix: save button created duplicate orders", "feat: export orders as csv", "auto deploy on main",
    "tests for bank webhook", "fix: fix the fix", "speed up order list", "feat: dark mode",
    "fix broken migration", "bump dependencies", "feat: passwordless login by e-mail", "why did this ever work",
    "fix: dashboard cache", "feat: filters on orders page", "remove dead code",
]


def demo_commits(year: int, seed: int = 7, lang: str = "en", scale: float = 1.0):
    rnd = random.Random(seed)
    tz = timezone(timedelta(hours=-3))
    msgs = MSGS if lang == "pt" else MSGS_EN
    you = "Você" if lang == "pt" else "You"
    out = []
    day = datetime(year, 1, 1, tzinfo=tz)
    n = 0
    while day.year == year:
        busy = (.82 if day.weekday() < 5 else .35) * scale
        if rnd.random() < busy:
            for _ in range(rnd.choice([1, 1, 2, 2, 3, 4, 6])):
                h = rnd.choices(range(24), weights=[3, 2, 1, .5, .2, .1, .3, 1, 3, 6, 8, 8, 4, 6, 8, 8, 7, 5, 3, 3, 4, 5, 5, 4])[0]
                when = day.replace(hour=h, minute=rnd.randrange(60))
                repo = rnd.choices(REPOS, weights=[30, 22, 18, 8, 4, 10])[0]
                files = [(rnd.randrange(1, 140), rnd.randrange(0, 60), f) for f in rnd.sample(FILES[repo], rnd.randint(1, min(3, len(FILES[repo]))))]
                n += 1
                out.append(Commit(f"{n:040x}", "you@example.dev", you, when, rnd.choice(msgs), repo, files))
        day += timedelta(days=1)
    # um commit de madrugada que todo mundo já fez
    out.append(Commit("f" * 40, "you@example.dev", you, datetime(year, 9, 12, 4, 52, tzinfo=tz),
                      "hotfix: produção caiu, não me pergunte" if lang == "pt" else "hotfix: prod is down, don't ask",
                      "api-pagamentos", [(12, 3, "app/services/pix.py")]))
    return out
