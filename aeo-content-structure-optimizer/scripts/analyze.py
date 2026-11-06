#!/usr/bin/env python3
"""Measure a markdown page against the ChatGPT-citation evidence base.

Usage: python3 analyze.py page.md [--html page.html] [--today YYYY-MM-DD] [--lang auto|en|fr]

--html: raw HTML of the live page. Enables real <table> counting and
        publish/modified date extraction (JSON-LD, meta tags, <time>).

Stdlib only. If TextBlob is installed, subjectivity is measured too; otherwise
it is reported as null and should be judged qualitatively.
Factor IDs match references/evidence.md.

--lang: rule set for language-dependent checks (default auto: <html lang>, then
        the share of French and English function words). French rules are a local
        addition to the Nectiv original; English behaviour is unchanged. The study
        benchmarks come from English content, so compare French pages directionally.
"""
import argparse
import datetime as dt
import json
import re
import sys

DEFINITIVE_RE = re.compile(
    r"\b(is defined as|refers to|is a|is an|is the|are the|means|is when|"
    r"consists of|is known as|stands for)\b"
    # Subject-first "X is/are Y" within the opening words of the sentence
    # (e.g. "Click fraud is the…", "Geographic leakage is traffic…").
    r"|^(?:[\w'’()\-]+\s){1,6}(?:is|are)\s(?!not\b)",
    re.I,
)
FLUFF_RE = re.compile(
    r"(in today'?s|fast-paced|ever-evolving|ever-changing|in this (article|post|guide)|"
    r"we will (discuss|explore|cover)|let'?s dive|look no further|when it comes to|"
    r"in the world of|it'?s no secret|have you ever wondered)",
    re.I,
)
SUMMARY_HEAD_RE = re.compile(
    r"(summary|conclusion|key takeaways|tl;?dr|bottom line|final thoughts|recap)", re.I
)
# Sentence-level signals that a claim is softer or vaguer than it needs to be.
# Each is a *candidate* for a definitive rewrite; the skill decides whether the
# page's own facts support a firmer statement (never overclaim).
# Generic stand-ins where a named entity (brand, tool, standard, study, number)
# would make the sentence citable [ENTITY].
GENERIC_REF_RE = re.compile(
    r"\b((?:many|some|several|various|other|leading|top|popular|certain|most) "
    r"(?:tools|platforms|companies|brands|providers|vendors|solutions|apps|experts|studies|"
    r"sources|sites|websites|publishers|businesses|advertisers|networks|databases)|"
    r"(?:studies|research|data|experts|reports) (?:show|shows|suggest|suggests|indicate|say)|"
    r"(?:a|the) (?:tool|platform|provider|vendor|solution|software|service|study|report)\b(?! called| named)|"
    r"(?:third-party|external) (?:[\w-]+ )?(?:databases|tools|providers|services|vendors)|"
    r"industry (?:data|research|benchmarks))", re.I)


HEDGE_RE = re.compile(
    r"\b(can|could|may|might|often|typically|generally|usually|tends? to|"
    r"somewhat|potentially|possibly|arguably|it is possible|in some cases|"
    r"to some extent|relatively)\b", re.I)
VAGUE_RE = re.compile(
    r"\b(several|various|many|numerous|a (?:number|variety|range) of|some|"
    r"certain|things|stuff|aspects?|nuances?|factors?|elements?)\b", re.I)
INDIRECT_OPENER_RE = re.compile(
    r"^(there (?:is|are|was|were)|it is|this is|these are|that is|"
    r"when it comes to|in terms of|one of the)\b", re.I)
ABSTRACT_VERB_RE = re.compile(
    r"\b(lies (?:within|in)|plays? a (?:key |critical |crucial |vital )?role|"
    r"is (?:a )?(?:key|critical|crucial|vital|essential) (?:component|part|factor|element)|"
    r"serves as|stems from)\b", re.I)


def definitive_candidates(sents):
    """Sentences worth a definitive rewrite, with the reasons each was flagged."""
    out = []
    for s in sents:
        reasons = []
        if INDIRECT_OPENER_RE.search(s):
            reasons.append("indirect opener")
        if ABSTRACT_VERB_RE.search(s):
            reasons.append("abstract verb phrase")
        h = sorted({m.group(0).lower() for m in HEDGE_RE.finditer(s)})
        if h:
            reasons.append("hedge: " + ", ".join(h))
        v = sorted({m.group(0).lower() for m in VAGUE_RE.finditer(s)})
        if v:
            reasons.append("vague quantifier: " + ", ".join(v))
        if reasons and not DEFINITIVE_RE.search(s):
            out.append({"sentence": s[:220] + ("…" if len(s) > 220 else ""), "reasons": reasons})
    return out


STOP = set(
    """a an the and or but if of to in on for with at by from as is are was were be
    been it this that these those what when where why how who which do does did can
    should will your you we our my i their its vs""".split()
)
# Capitalized words that are usually not entities when mid-sentence.
NON_ENTITY_CAPS = set("""I I'm I've It's The A An This That These Those""".split())


# --- French rules. use_language("fr") swaps them in for the English ones above.
LANG = "en"
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'&.+-]*")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
ELISION_RE = re.compile(r"\b(?:l|d|j|n|s|t|m|c|qu|jusqu|lorsqu|puisqu|quoiqu)['’](?=\w)", re.I)
EN_RULES = {}
FR_RULES = {
    "DEFINITIVE_RE": re.compile(
        r"(?<![nN]['’])\b(?:est|sont) (?:un|une|le|la|l['’]|les|des|définie?s? comme|appelée?s?|connue?s? comme)"
        r"|\b(?:se définit|désigne(?:nt)?|correspond(?:ent)? à|signifie(?:nt)?|consiste(?:nt)? (?:à|en)|"
        r"regroupe(?:nt)?|on appelle)\b"
        # Subject-first "X est/sont Y" in the opening words, without a bare pronoun as subject.
        r"|^(?!(?:il|elle|ils|elles|ce|cela|ceci|ça|on|c['’])\b)(?:[\w'’()\-]+\s){1,6}(?:est|sont)\s(?!pas\b)",
        re.I),
    "FLUFF_RE": re.compile(
        r"(de nos jours|à l['’]heure (?:actuelle|où)|dans le monde d['’]aujourd['’]hui|dans un monde|"
        r"en (?:constante|perpétuelle) évolution|dans (?:cet article|ce guide|ce billet)|"
        r"nous allons (?:voir|aborder|explorer|découvrir)|sans plus attendre|ne cherchez plus|"
        r"(?:lorsqu['’]|quand )il s['’]agit de|dans le monde de|n['’]est un secret pour personne|"
        r"vous vous êtes (?:déjà )?demandé|il va sans dire|vous l['’]aurez compris)", re.I),
    "SUMMARY_HEAD_RE": re.compile(
        r"(résumé|conclusion|pour conclure|points? clés?|l['’]essentiel|à retenir|en bref|synthèse|bilan)", re.I),
    "GENERIC_REF_RE": re.compile(
        r"\b((?:de nombreux|de nombreuses|plusieurs|certains|certaines|divers|diverses|différents|différentes|"
        r"beaucoup de|la plupart des|les principaux|les principales|d['’]autres) "
        r"(?:outils|plateformes|entreprises|sociétés|marques|fournisseurs|prestataires|solutions|applications|"
        r"experts|spécialistes|études|sources|sites|éditeurs|acteurs|professionnels|réseaux|bases de données)|"
        r"(?:études|recherches|données|experts|rapports|chiffres) (?:montrent|indiquent|suggèrent|disent|révèlent|confirment)|"
        r"(?:selon|d['’]après) (?:les|des|une|un|certains) (?:études?|experts?|rapports?|spécialistes?)|"
        r"(?:le|la|l['’]) ?(?:outil|plateforme|prestataire|fournisseur|solution|logiciel|service|étude|rapport)\b"
        r"(?! (?:appelée?|nommée?))|"
        r"(?:outils|bases de données|prestataires|services|fournisseurs) (?:tiers|tierces|externes)|"
        r"(?:données|études?) (?:du secteur|sectorielles?))", re.I),
    "HEDGE_RE": re.compile(
        r"\b(peut|peuvent|pourrait|pourraient|pourra|pourront|souvent|généralement|habituellement|en général|"
        r"typiquement|tend à|tendent à|potentiellement|éventuellement|possiblement|il est possible|"
        r"dans certains cas|parfois|relativement|plutôt|en quelque sorte|dans une certaine mesure|"
        r"sans doute|semble|semblent|probablement)\b", re.I),
    "VAGUE_RE": re.compile(
        r"\b(plusieurs|divers|diverses|différents|différentes|nombreux|nombreuses|beaucoup|certains|certaines|"
        r"quelques|un certain nombre|une variété de|une gamme de|tous types|choses?|aspects?|nuances?|"
        r"facteurs?|éléments?)\b", re.I),
    "INDIRECT_OPENER_RE": re.compile(
        r"^(il y a|il existe|il s['’]agit|il est|c['’]est|ce sont|ceci est|cela est|"
        r"(?:lorsqu['’]|quand )il s['’]agit|en termes de|en matière de|au niveau de|l['’]une? des)", re.I),
    "ABSTRACT_VERB_RE": re.compile(
        r"\b(réside(?:nt)? dans|joue(?:nt)? un rôle(?: (?:clé|essentiel|crucial|majeur|central|important|déterminant))?|"
        r"(?:est|sont|constitue(?:nt)?) (?:un|une|des) (?:élément|composante|facteur|levier|enjeu)s?(?: (?:clé|essentiel|essentielle|crucial|cruciale|majeur|majeure))?|"
        r"sert de|servent de|découle(?:nt)? de|s['’]inscrit dans|s['’]inscrivent dans|permet(?:tent)? de)\b", re.I),
    "STOP": set(
        """le la les un une des du de et ou mais si au aux en dans sur pour par avec sans sous vers chez
        que qui quoi dont quand comment pourquoi quel quelle quels quelles est sont être été ce cet cette
        ces il elle ils elles nous vous votre vos notre nos leur leurs son sa ses ne pas plus""".split()),
    "NON_ENTITY_CAPS": set(
        """Le La Les Un Une Des Du De Et Ou Mais Si Au Aux En Dans Sur Pour Par Avec Sans Sous Vers Chez
        À Que Qui Quand Comment Pourquoi Quel Quelle Quels Quelles Ce Cet Cette Ces Il Elle Ils Elles
        On Nous Vous Votre Vos Notre Nos Leur Leurs Son Sa Ses Tout Tous Toute Toutes""".split()),
    "PRONOUN_LEAD_RE": re.compile(
        r"^(?:C['’]|(?:Il|Elle|Ils|Elles|Ce|Cet|Cette|Ces|Cela|Ceci|Ça|Son|Sa|Ses|Leur|Leurs|On|Voici|Celui|Celle|Ceux|Celles)(?!\w))"),
    "TAKEAWAY_HEAD_RE": re.compile(
        r"(points? clés?|l['’]essentiel|à retenir|en bref|en résumé|résumé|synthèse|réponse rapide)", re.I),
    "KEY_TAKEAWAY_NAME_RE": re.compile(r"points? clés?|l['’]essentiel|à retenir", re.I),
    "VISIBLE_UPDATED_RE": re.compile(
        r"(dernière mise à jour|mise à jour|mis à jour|actualisée?|modifiée?|révisée?)(?: le)?\s*:?\s*"
        r"((?:1er|\d{1,2})\s+[a-zéû]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|[a-zéû]+\s+\d{4})",
        re.I),
    "WORD_RE": re.compile(r"[^\W_][\w'’&.+-]*"),
    "SENT_SPLIT_RE": re.compile(r"(?<=[.!?…])\s+(?=[A-ZÀ-ÖØ-Þ0-9\"'«“(])"),
}
FR_MONTHS = {m: i + 1 for i, m in enumerate(
    "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split())}
FR_MARKERS = set("le la les des du une et est sont pour dans avec vos votre nous vous sur que qui".split())
EN_MARKERS = set("the and is are for with your you we our that this of to in on".split())


def detect_language(md, html=None):
    if html:
        m = re.search(r"<html[^>]*\blang=[\"']?([a-zA-Z]{2})", html)
        if m:
            return "fr" if m.group(1).lower() == "fr" else "en"
    toks = re.findall(r"[^\W\d_]+", md.lower())
    fr = sum(t in FR_MARKERS for t in toks)
    en = sum(t in EN_MARKERS for t in toks)
    return "fr" if fr > en else "en"


def use_language(lang):
    """Rebind the language-dependent module rules. English is the untouched default."""
    global LANG
    g = globals()
    if not EN_RULES:
        EN_RULES.update({k: g[k] for k in FR_RULES})
    g.update(FR_RULES if lang == "fr" else EN_RULES)
    LANG = lang


def strip_md(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`>|]", " ", text)
    return text


def sentences(text):
    parts = SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if len(p.split()) >= 3]


def words(text):
    if LANG == "fr":
        text = ELISION_RE.sub("", text)  # "d'Orléans" -> "Orléans", one word and an entity
        return [t.rstrip(".") for t in WORD_RE.findall(text)]
    return WORD_RE.findall(text)


def syllables(word):
    w = word.lower().strip(".'")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def syllables_fr(word):
    """Rough French count: vowel groups, ignoring a final mute e/es."""
    w = re.sub(r"[^\w]", "", word.lower())
    n = len(re.findall(r"[aeiouyàâäéèêëîïôöùûüÿœæ]+", w))
    if n > 1 and re.search(r"[^aeiouyàâäéèêëîïôöùûüÿœæ]es?$", w):
        n -= 1
    return max(1, n)


def kandel_moles(sents):
    """French Flesch adaptation (Kandel & Moles, 1958): higher is easier. Heuristic
    syllable count; not comparable with the Flesch-Kincaid grade in the studies."""
    ws = [w for s in sents for w in words(s)]
    if not sents or not ws:
        return None
    syl = sum(syllables_fr(w) for w in ws)
    return round(207 - 1.015 * len(ws) / len(sents) - 73.6 * syl / len(ws), 1)


def fk_grade(sents):
    if LANG == "fr":
        return None  # English formula: meaningless on French text
    ws = [w for s in sents for w in words(s)]
    if not sents or not ws:
        return None
    syl = sum(syllables(w) for w in ws)
    return round(0.39 * len(ws) / len(sents) + 11.8 * syl / len(ws) - 15.59, 1)


def entity_tokens(sent):
    """Heuristic proper-noun detector: capitalized/acronym/CamelCase tokens that
    are not sentence-initial, plus numbers with units/years. Approximate."""
    toks = words(sent)
    ents = []
    for i, t in enumerate(toks):
        if t in NON_ENTITY_CAPS:
            continue
        if re.fullmatch(r"[A-Z]{2,}[0-9]*s?", t) or re.search(r"[a-z][A-Z]", t):
            ents.append(t)  # acronyms, CamelCase (HubSpot)
        elif LANG == "fr" and i == 0 and re.search(r"-[A-ZÀ-ÖØ-Þ]", t):
            ents.append(t)  # sentence-initial compound names (Saint-Étienne, Aix-en-Provence)
        elif i > 0 and t[0].isupper():
            ents.append(t)
        elif re.fullmatch(r"(19|20)\d\d", t):
            ents.append(t)  # years are grounding anchors
        elif re.search(r"\d", t):
            ents.append(t)  # specific numbers ("21-50", "10", "86") are checkable facts
    return ents, len(toks)


def subjectivity(text):
    if LANG == "fr":
        return None  # TextBlob's default lexicon is English
    try:
        from textblob import TextBlob  # optional
    except ImportError:
        return None
    return round(TextBlob(text).sentiment.subjectivity, 2)


TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def find_tables(md):
    """Markdown pipe tables (what html_to_md.py emits for HTML <table>). Returns
    [{position_pct, rows, cols, header}] with position = share of preceding text."""
    lines = md.split("\n")
    total = len(words(strip_md(md))) or 1
    tables = []
    for i, line in enumerate(lines):
        if i == 0 or not TABLE_SEP_RE.match(line) or "|" not in lines[i - 1]:
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip().startswith("|"):
            j += 1
        before = len(words(strip_md("\n".join(lines[: i - 1]))))
        header = [c.strip() for c in lines[i - 1].strip().strip("|").split("|")]
        tables.append({
            "position_pct": round(100 * before / total, 1),
            "rows": j - i - 1,
            "cols": len(header),
            "header": header,
        })
    return tables


DATE_KEYS = {
    "modified": [
        r'"dateModified"\s*:\s*"([^"]+)"',
        r'property=["\']article:modified_time["\']\s+content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\']\s+property=["\']article:modified_time',
        r'property=["\']og:updated_time["\']\s+content=["\']([^"\']+)',
    ],
    "published": [
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time',
    ],
}
VISIBLE_UPDATED_RE = re.compile(
    r"(last updated|updated on|updated:|last modified|reviewed on)\s*:?\s*"
    r"([A-Z][a-z]+\.? \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|[A-Z][a-z]+ \d{4})",
    re.I,
)


def parse_date(raw):
    raw = raw.strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return dt.date.fromisoformat(m.group(1))
    if LANG == "fr":
        try:
            m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)  # day first
            if m:
                return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            m = re.fullmatch(r"(?:(1er|\d{1,2})\s+)?([a-zéû]+)\s+(\d{4})", raw.lower())
            if m and m.group(2) in FR_MONTHS:
                return dt.date(int(m.group(3)), FR_MONTHS[m.group(2)], int((m.group(1) or "1").replace("er", "")))
        except ValueError:
            pass
        return None
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b. %d, %Y", "%m/%d/%Y", "%B %Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def freshness(md, html, today):
    out = {"today": today.isoformat()}
    if html:
        for kind, pats in DATE_KEYS.items():
            found = None
            for pat in pats:
                m = re.search(pat, html, re.I)
                if m and parse_date(m.group(1)):
                    found = parse_date(m.group(1))
                    break
            out[f"{kind}_date_metadata"] = found.isoformat() if found else None
    vis = VISIBLE_UPDATED_RE.search(html or md)
    vis_date = parse_date(vis.group(2)) if vis else None
    out["visible_updated_label"] = vis.group(0)[:60] if vis else None
    cands = [d for d in (out.get("modified_date_metadata"), out.get("published_date_metadata"),
                         vis_date.isoformat() if vis_date else None) if d]
    best = max(cands) if cands else None  # latest known date; a modified < published bug shouldn't age the page
    mod, pub = out.get("modified_date_metadata"), out.get("published_date_metadata")
    out["metadata_conflict"] = (
        f"dateModified ({mod}) is earlier than datePublished ({pub})" if mod and pub and mod < pub else None)
    out["days_since_update"] = (today - dt.date.fromisoformat(best)).days if best else None
    # In-content staleness: years mentioned in body text (titles like "Best X 2024").
    years = sorted({int(y) for y in re.findall(r"\b(20[0-3]\d)\b", md) if int(y) <= today.year})
    out["years_mentioned"] = years
    out["latest_year_mentioned"] = years[-1] if years else None
    out["stale_year_reference"] = bool(years) and years[-1] < today.year
    return out


def parse_blocks(md):
    """Return list of (kind, level, text) where kind is 'h' or 'p'."""
    blocks = []
    for raw in re.split(r"\n\s*\n", md):
        raw = raw.strip()
        if not raw:
            continue
        for line in raw.split("\n"):
            m = re.match(r"^(#{1,6})\s+(.*)", line)
            if m:
                blocks.append(("h", len(m.group(1)), strip_md(m.group(2)).strip()))
                raw = raw.replace(line, "", 1)
        raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("|"))  # tables aren't prose
        # Each list item is its own sentence: strip the marker, end it with a period.
        raw = "\n".join(
            (re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", l).rstrip() + ("" if re.search(r"[.!?:]$", l.rstrip()) else "."))
            if re.match(r"^\s*([-*+]|\d+[.)])\s+", l) else l
            for l in raw.split("\n"))
        body = strip_md(raw).strip()
        if body:
            blocks.append(("p", 0, re.sub(r"\s+", " ", body)))
    return blocks


def content_words(text):
    out = {w.lower() for w in words(text) if w.lower() not in STOP and len(w) > 2}
    # French echo check: "déchet" under a heading about "déchets" is still an echo.
    return {w.rstrip("sx.") for w in out} if LANG == "fr" else out


LIST_LINE_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+\S")
PRONOUN_LEAD_RE = re.compile(r"^(It|This|That|These|Those|They|Its|Their|He|She|Here)\b")


TAKEAWAY_HEAD_RE = re.compile(
    r"(key takeaways?|takeaways|tl;?dr|key points|at a glance|in brief|summary|quick answer)", re.I)
KEY_TAKEAWAY_NAME_RE = re.compile(r"takeaway", re.I)


def key_takeaways(md):
    """House rule: a Key Takeaways section with 3-6 bullets as the first thing on
    the page, directly under the H1 (Study 1: 44.2% of citations come from the
    first 30%)."""
    lines = md.split("\n")
    total = len(words(strip_md(md))) or 1
    found = []
    for i, l in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", l)
        if not m or not TAKEAWAY_HEAD_RE.search(m.group(2)):
            continue
        before = len(words(strip_md("\n".join(lines[:i]))))
        # first on the page = nothing but the H1 title (and blank lines) above it
        is_first = all(not x.strip() or re.match(r"^#\s", x) for x in lines[:i])
        bullets, prose = 0, 0
        for l2 in lines[i + 1:]:
            if re.match(r"^#{1,6}\s", l2):
                break
            if LIST_LINE_RE.match(l2):
                bullets += 1
            elif l2.strip() and not l2.strip().startswith("|"):
                if bullets:  # the list has ended; what follows (e.g. the intro) isn't part of it
                    break
                prose += 1
        found.append({"heading": strip_md(m.group(2)).strip(), "position_pct": round(100 * before / total, 1),
                      "bullets": bullets, "prose_lines": prose, "is_first": is_first,
                      "is_key_takeaways": bool(KEY_TAKEAWAY_NAME_RE.search(m.group(2)))})
    best = next((f for f in found if f["is_key_takeaways"]), found[0] if found else None)
    passes = bool(best and best["is_key_takeaways"] and 3 <= best["bullets"] <= 6 and best["is_first"])
    return {
        "section": best,
        "other_summary_sections": [f for f in found if f is not best],
        "passes": passes,
        "rule": "A 'Key Takeaways' section with 3-6 bullets as the first thing on the page, under the H1",
        "benchmark": "44.2% of ChatGPT citations come from the first 30% of a page [POS-DOC]",
    }


def chunk_structure(md):
    """Signals for chunk self-containment (Study 4): dense prose vs.
    structured sections. ~100-token chunks ≈ 75 words."""
    lines = md.split("\n")
    list_lines = [l for l in lines if LIST_LINE_RE.match(l)]
    list_words = sum(len(words(l)) for l in list_lines)
    total = len(words(strip_md(md))) or 1

    # Sections = text between headings (H2+; H1 treated as title).
    sections, cur_head, cur = [], "(before first heading)", []
    for l in lines:
        m = re.match(r"^(#{2,6})\s+(.*)", l)
        if m:
            sections.append((cur_head, " ".join(cur)))
            cur_head, cur = strip_md(m.group(2)).strip(), []
        elif not re.match(r"^#\s", l):
            cur.append(l)
    sections.append((cur_head, " ".join(cur)))
    sec = [(h, len(words(strip_md(t)))) for h, t in sections if words(strip_md(t))]

    long_paras, pronoun_leads, para_lens = [], [], []
    after_heading = True
    for raw in re.split(r"\n\s*\n", md):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("#"):
            after_heading = True
            continue
        if LIST_LINE_RE.match(raw) or raw.startswith("|"):
            after_heading = False
            continue
        text = re.sub(r"\s+", " ", strip_md(raw)).strip()
        n = len(words(text))
        para_lens.append(n)
        if n > 120:
            long_paras.append(f"{n}w: " + text[:100] + "…")
        if after_heading and PRONOUN_LEAD_RE.match(text):
            pronoun_leads.append(text[:100])
        after_heading = False

    return {
        "list_items": len(list_lines),
        "pct_words_in_lists": round(100 * list_words / total, 1),
        "sections": len(sec),
        "avg_section_words": round(sum(n for _, n in sec) / max(1, len(sec)), 1),
        "sections_over_300_words": [f"{h} ({n}w)" for h, n in sec if n > 300],
        "paragraphs_over_120_words": len(long_paras),
        "avg_paragraph_words": round(sum(para_lens) / max(1, len(para_lens)), 1),
        "longest_paragraph_words": max(para_lens, default=0),
        "long_paragraph_examples": long_paras[:5],
        "section_openers_starting_with_pronoun": pronoun_leads[:8],
        "benchmark": "controlled test: Q&A > structured (headings/lists) >> dense prose on query-chunk similarity",
    }


def analyze(md, html=None, today=None, lang="auto"):
    lang = detect_language(md, html) if lang == "auto" else lang
    use_language(lang)
    today = today or dt.date.today()
    blocks = parse_blocks(md)
    paras = [b[2] for b in blocks if b[0] == "p"]
    body = " ".join(paras)
    all_sents = sentences(body)
    total_words = len(words(body)) or 1

    # Positional bands by cumulative word count.
    bands = {"intro_0_30": [], "middle_30_70": [], "end_70_100": []}
    cum = 0
    for p in paras:
        pos = cum / total_words
        key = "intro_0_30" if pos < 0.3 else "middle_30_70" if pos < 0.7 else "end_70_100"
        bands[key].append(p)
        cum += len(words(p))

    def band_stats(ps):
        ss = sentences(" ".join(ps))
        ent = tot = 0
        for s in ss:
            e, n = entity_tokens(s)
            ent += len(e)
            tot += n
        return {
            "words": sum(len(words(p)) for p in ps),
            "sentences": len(ss),
            "entity_density_pct": round(100 * ent / tot, 1) if tot else 0,
            "definitive_sentences": sum(bool(DEFINITIVE_RE.search(s)) for s in ss),
        }

    # Front-loading: where is the first definitive sentence?
    first_def_pos = None
    cum = 0
    for s in all_sents:
        if DEFINITIVE_RE.search(s):
            first_def_pos = round(100 * cum / total_words, 1)
            break
        cum += len(words(s))

    intro_text = " ".join(paras[:2])
    fluff = sorted({m.group(0).lower() for m in FLUFF_RE.finditer(intro_text)})

    # Headings: question rate + entity echo with following paragraph.
    headings = []
    for i, (kind, level, text) in enumerate(blocks):
        if kind != "h" or level == 1:
            continue
        nxt = next((b[2] for b in blocks[i + 1:] if b[0] == "p"), "")
        first_words = " ".join(words(nxt)[:8])
        echo = bool(content_words(text) & content_words(first_words))
        fs = sentences(nxt)[:1]
        headings.append({
            "level": level,
            "text": text,
            "is_question": text.rstrip().endswith("?"),
            "answer_echoes_heading": echo,
            "answer_first_sentence_definitive": bool(fs and DEFINITIVE_RE.search(fs[0])),
            "answer_opening": first_words,
        })
    q_heads = [h for h in headings if h["is_question"]]

    # Summary section near the end?
    h_positions = []
    cum = 0
    for kind, level, text in blocks:
        if kind == "h":
            h_positions.append((cum / total_words, text))
        else:
            cum += len(words(text))
    has_summary = any(pos >= 0.6 and SUMMARY_HEAD_RE.search(t) for pos, t in h_positions)

    # Sentence-level stats.
    ent = tot = 0
    long_sents = []
    zero_entity_sents = 0
    zero_entity_examples, generic_refs, entity_counts = [], [], {}
    for s in all_sents:
        e, n = entity_tokens(s)
        ent += len(e)
        tot += n
        for t in e:
            entity_counts[t] = entity_counts.get(t, 0) + 1
        if not e:
            zero_entity_sents += 1
            zero_entity_examples.append(s[:200] + ("…" if len(s) > 200 else ""))
        g = sorted({m.group(0).lower() for m in GENERIC_REF_RE.finditer(s)})
        if g:
            generic_refs.append({"sentence": s[:200] + ("…" if len(s) > 200 else ""), "generic": g})
        if n > 35:
            long_sents.append(s[:160] + ("…" if len(s) > 160 else ""))

    tables = find_tables(md)
    html_tables = len(re.findall(r"<table\b", html, re.I)) if html else None

    return {
        "language": lang,
        "language_note": None if lang == "en" else (
            "French rules applied. The benchmarks come from English-language studies: compare directionally. "
            "READ uses the Kandel-Moles score (higher is easier), not the Flesch-Kincaid grade."),
        "word_count": total_words,
        "paragraphs": len(paras),
        "POS-DOC": {
            "bands": {k: band_stats(v) for k, v in bands.items()},
            "first_definitive_sentence_at_pct": first_def_pos,
            "intro_fluff_phrases": fluff,
            "intro_preview": intro_text[:400],
            "has_summary_section_near_end": has_summary,
        },
        "DEFINITIVE": {
            "pct_sentences_definitive": round(100 * sum(bool(DEFINITIVE_RE.search(s)) for s in all_sents) / max(1, len(all_sents)), 1),
            "benchmark": "cited 36.2% vs non-cited 20.2%",
            "rewrite_candidates": definitive_candidates(all_sents),
        },
        "QA": {
            "headings_total": len(headings),
            "question_headings": len(q_heads),
            "pct_question_headings": round(100 * len(q_heads) / max(1, len(headings)), 1),
            "question_headings_with_entity_echo": sum(h["answer_echoes_heading"] for h in q_heads),
            "headings": headings,
        },
        "ENTITY": {
            "entity_density_pct": round(100 * ent / tot, 1) if tot else 0,
            "pct_sentences_with_zero_entities": round(100 * zero_entity_sents / max(1, len(all_sents)), 1),
            "zero_entity_sentences": zero_entity_examples,
            "generic_references": generic_refs,
            "entities_on_page": sorted(entity_counts, key=lambda k: -entity_counts[k])[:40],
            "targets": "heuristic density >= 12% overall and >= 15% in the intro and Key Takeaways; "
                       "sentences with no entity <= 25%",
            "benchmark": "cited 20.6% vs normal English 5-8% (heuristic count; compare directionally)",
        },
        "READ": {
            "flesch_kincaid_grade": fk_grade(all_sents),
            "kandel_moles_score": kandel_moles(all_sents) if lang == "fr" else None,
            "avg_sentence_words": round(tot / max(1, len(all_sents)), 1),
            "sentences_over_35_words": len(long_sents),
            "long_sentence_examples": long_sents[:5],
            "benchmark": "cited FK 16 vs non-cited 19.1",
        },
        "TAKEAWAYS": key_takeaways(md),
        "CHUNK": chunk_structure(md),
        "TABLE": {
            "markdown_tables": len(tables),
            "html_table_elements": html_tables,
            "first_table_at_pct": tables[0]["position_pct"] if tables else None,
            "tables": tables,
            "benchmark": "30% of ChatGPT-cited pages have a <table> vs 13% of Google results (2.3x)",
            "note": "Counts markdown pipe tables only. For live URLs, confirm a real HTML <table> in raw HTML (div grids and images don't count).",
        },
        "FRESH": dict(freshness(md, html, today), benchmark=(
            "cited pages: 35% updated <3mo, 53% <6mo, ~70%+ <12mo; commercial queries: "
            "60% <6mo, 83% <12mo; SaaS/finance/news window ~3mo")),
        "SUBJ": {
            "subjectivity": subjectivity(body),
            "benchmark": "cited ~0.47; avoid <0.2 (dry) and >0.7 (hype)",
            "note": None if subjectivity("x") is not None else (
                "No French lexicon — judge qualitatively" if lang == "fr"
                else "TextBlob not installed — judge qualitatively"),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown")
    ap.add_argument("--html")
    ap.add_argument("--today", type=dt.date.fromisoformat)
    ap.add_argument("--lang", choices=["auto", "en", "fr"], default="auto")
    a = ap.parse_args()
    md = open(a.markdown, encoding="utf-8").read()
    html = open(a.html, encoding="utf-8", errors="ignore").read() if a.html else None
    print(json.dumps(analyze(md, html, a.today, a.lang), indent=2))
