"""Sentimento de notícias por léxico financeiro em português.

Abordagem gratuita, offline e auditável: o resultado lista os termos que
contribuíram para o score. Limitações: não entende ironia, contexto, nem
quem é afetado (ex.: "queda do petróleo" pode ser ruim para PETR4 e neutra
para ITUB4); a negação tratada é apenas a imediatamente anterior.
"""

import re
import unicodedata

# Termos (sem acento) -> peso. Palavra exata por padrão; "*" final = prefixo
# (cobre flexões, ex.: "valoriz*" casa "valorizacao", "valorizou").
POSITIVE = {
    "alta": 1, "altas": 1, "sobe": 1, "sobem": 1, "subiu": 1, "subir": 1, "dispar*": 1.5,
    "avanc*": 1, "valoriz*": 1, "lucro*": 1, "lucrou": 1, "recorde*": 1, "cresc*": 1,
    "supera*": 1, "ganho*": 1, "ganha": 1, "ganham": 1, "otimis*": 1, "recomendacao de compra": 1.5, "eleva": 1,
    "elevou": 1, "upgrade": 1.5, "dividendo*": 1, "proventos": 1, "jcp": 1, "recompra": 1,
    "positiv*": 1, "melhor": 1, "expansao": 1, "acima do esperado": 1.5, "salta": 1.5,
    "saltou": 1.5, "recupera*": 1, "impulsion*": 1, "aprova": 0.5, "aprovou": 0.5,
}
NEGATIVE = {
    "queda*": 1, "cai": 1, "caem": 1, "caiu": 1, "cair": 1, "despenc*": 1.5, "recua*": 1,
    "recuo": 1, "desvaloriz*": 1, "prejuizo*": 1.5, "perda*": 1, "perde": 1, "perdeu": 1,
    "crise": 1, "rebaix*": 1.5, "downgrade": 1.5, "pessimis*": 1, "risco*": 0.5,
    "investiga*": 1, "multa*": 1, "abaixo do esperado": 1.5, "negativ*": 1, "fraco": 1,
    "fraca": 1, "pior": 1, "tomba*": 1.5, "afunda*": 1.5, "inadimpl*": 1, "desastre": 1.5,
    "interferencia": 1, "recomendacao de venda": 1.5, "pressiona*": 1, "greve": 1,
}
NEGATIONS = {"nao", "sem", "nem", "nunca"}
NEUTRAL_BAND = 0.15


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.lower()).strip()


def _compile(term):
    stem = term.endswith("*")
    body = re.escape(term.rstrip("*"))
    return re.compile(r"\b" + body + (r"\w*" if stem else r"\b"))


# Termos mais longos primeiro, para que frases prevaleçam sobre palavras soltas.
_PATTERNS = sorted(((_compile(t), sign * w, len(t)) for lex, sign in ((POSITIVE, 1), (NEGATIVE, -1))
                    for t, w in lex.items()), key=lambda x: -x[2])


def classify(text: str) -> dict:
    """Retorna {'label', 'score' em [-1,1], 'terms': [termos casados com sinal]}."""
    norm = _norm(text)
    total, hits, used = 0.0, [], []
    for pat, weight, _ in _PATTERNS:
        for m in pat.finditer(norm):
            if any(s < m.end() and m.start() < e for s, e in used):  # trecho já contado
                continue
            used.append(m.span())
            before = norm[:m.start()].split()[-2:]
            negated = bool(NEGATIONS & set(before))
            w = -weight if negated else weight
            total += w
            hits.append(("+" if w > 0 else "-") + m.group(0) + (" (negado)" if negated else ""))
    # Satura suavemente: 3 pontos líquidos ~ 0.75.
    score = max(-1.0, min(1.0, total / (abs(total) + 1))) if total else 0.0
    label = "positivo" if score > NEUTRAL_BAND else "negativo" if score < -NEUTRAL_BAND else "neutro"
    return {"label": label, "score": round(score, 3), "terms": hits}
