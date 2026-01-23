from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable, Tuple

ROLE_IDS = [
    "OPS",
    "ADMIN",
    "SALES",
    "SUPPORT",
    "LOGISTICS",
    "MAINTENANCE",
    "CONTENT",
    "ANALYTICS",
]
UNKNOWN = "UNKNOWN"

STOPWORDS = [
    "m w d",
    "mw d",
    "mwd",
    "vollzeit",
    "teilzeit",
    "minijob",
    "gesucht",
    "ab sofort",
    "sofort",
    "jetzt",
    "bewerben",
    "unbefristet",
    "befristet",
    "homeoffice",
    "hybrid",
    "quereinsteiger",
    "junior",
    "senior",
    "d",
    "w",
    "m",
]

WEAK_CAP = 4
NEUTRAL_WEAK_CAP = 2

NEUTRAL_WEAK = [
    "service",
    "berater",
    "kunden",
    "lager",
    "dokument",
    "office",
    "admin",
    "support",
]

RAW_STRONG = {
    "SALES": [
        "vertrieb",
        "akquise",
        "closing",
        "key account",
        "account manager",
        "verkaeufer",
        "verkauf",
        "sales manager",
        "sales representative",
    ],
    "SUPPORT": [
        "kundenservice",
        "callcenter",
        "hotline",
        "helpdesk",
        "service desk",
        "1st level",
        "2nd level",
        "customer service",
        "support agent",
    ],
    "ADMIN": [
        "backoffice",
        "rezeption",
        "empfang",
        "sekretariat",
        "assistenz",
        "sachbearbeiter",
        "buerokaufmann",
        "office manager",
    ],
    "LOGISTICS": [
        "logistik",
        "zusteller",
        "lieferfahrer",
        "kurier",
        "spedition",
        "transport",
        "fahrer",
        "dispatch",
        "disponent",
    ],
    "OPS": [
        "produktionsmitarbeiter",
        "maschinenbediener",
        "fertigung",
        "qualitaetskontrolle",
        "sortierer",
        "assembly line",
        "production",
    ],
    "MAINTENANCE": [
        "servicetechniker",
        "instandhaltung",
        "wartung",
        "installation",
        "monteur",
        "stoerung",
        "kundendiensttechniker",
    ],
    "CONTENT": [
        "content creator",
        "video editor",
        "grafikdesigner",
        "designer",
        "fotograf",
        "videograf",
        "ux designer",
    ],
    "ANALYTICS": [
        "data analyst",
        "business analyst",
        "reporting",
        "dashboard",
        "etl",
        "sql",
        "automation",
        "bi",
    ],
}

RAW_WEAK = {
    "SALES": [
        "crm",
        "angebot",
        "lead",
        "abschluss",
        "berater",
        "aussendienst",
        "innendienst",
        "kundenberater",
    ],
    "SUPPORT": [
        "ticket",
        "ticketsystem",
        "chat support",
        "kundenbetreuung",
        "reklamation",
        "anfragen",
        "telefonservice",
        "поддержк",
        "клиент",
        "колл",
        "звонк",
    ],
    "ADMIN": [
        "administration",
        "buero",
        "dokument",
        "ablage",
        "datenerfassung",
        "stammdaten",
        "poststelle",
        "auftragsbearbeitung",
        "документ",
        "офис",
        "админ",
        "секрет",
    ],
    "LOGISTICS": [
        "route",
        "tour",
        "lieferung",
        "fuhrpark",
        "paket",
        "sendung",
        "verladung",
        "entladung",
        "доставк",
        "курьер",
        "склад",
    ],
    "OPS": [
        "packen",
        "packing",
        "picker",
        "picking",
        "packer",
        "scannen",
        "sortieren",
        "schicht",
        "kommissionierer",
        "kommissionierung",
    ],
    "MAINTENANCE": [
        "reparatur",
        "ersatzteile",
        "werkzeug",
        "serviceeinsatz",
        "elektriker",
        "mechatroniker",
        "hausmeister",
        "ремонт",
        "техник",
        "монтаж",
    ],
    "CONTENT": [
        "video",
        "schnitt",
        "youtube",
        "blog",
        "copywriting",
        "texter",
        "social media",
        "branding",
        "контент",
        "видео",
        "дизайн",
    ],
    "ANALYTICS": [
        "analyse",
        "auswertung",
        "kpi",
        "optimierung",
        "statistik",
        "research",
        "forecast",
        "modell",
        "аналит",
        "данные",
        "отчет",
    ],
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_phrases(phrases: Iterable[str]) -> list[str]:
    return [normalize_text(phrase) for phrase in phrases if phrase]


NORMALIZED_STOPWORDS = _normalize_phrases(STOPWORDS)
NEUTRAL_WEAK_SET = set(_normalize_phrases(NEUTRAL_WEAK))

STRONG = {role: _normalize_phrases(phrases) for role, phrases in RAW_STRONG.items()}
WEAK = {role: _normalize_phrases(phrases) for role, phrases in RAW_WEAK.items()}


def normalize(text: str) -> str:
    text = normalize_text(text)
    padded = f" {text} "
    for phrase in NORMALIZED_STOPWORDS:
        if phrase:
            padded = padded.replace(f" {phrase} ", " ")
    return re.sub(r"\s+", " ", padded).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def classify_role_family(
    title: str,
    summary: str | None = None,
    *,
    return_debug: bool = False,
) -> str | Tuple[str, dict[str, object]]:
    combined = " ".join(part for part in [title, summary or ""] if part)
    normalized = normalize(combined)
    scores = defaultdict(int)
    strong_hits: dict[str, list[str]] = {role: [] for role in ROLE_IDS}
    weak_hits: dict[str, list[str]] = {role: [] for role in ROLE_IDS}
    weak_points = defaultdict(int)
    neutral_weak_points = defaultdict(int)

    for role, phrases in STRONG.items():
        for phrase in phrases:
            if contains_phrase(normalized, phrase):
                scores[role] += 3
                strong_hits[role].append(phrase)

    for role, phrases in WEAK.items():
        for phrase in phrases:
            if not contains_phrase(normalized, phrase):
                continue
            is_neutral = phrase in NEUTRAL_WEAK_SET
            if is_neutral and neutral_weak_points[role] >= NEUTRAL_WEAK_CAP:
                continue
            if weak_points[role] >= WEAK_CAP:
                continue
            weak_points[role] += 1
            if is_neutral:
                neutral_weak_points[role] += 1
            scores[role] += 1
            weak_hits[role].append(phrase)

    sorted_roles = sorted(
        ROLE_IDS,
        key=lambda role: scores[role],
        reverse=True,
    )
    best_role = sorted_roles[0]
    best_score = scores[best_role]
    second_role = sorted_roles[1] if len(sorted_roles) > 1 else UNKNOWN
    second_score = scores[second_role] if second_role != UNKNOWN else 0

    has_strong = len(strong_hits[best_role]) > 0
    confident = (has_strong and best_score >= 3) or best_score >= 4
    if not confident or (best_score - second_score) < 2:
        best_role = UNKNOWN

    if scores["SALES"] >= 3 and scores["SUPPORT"] >= 3:
        best_role = UNKNOWN
    if scores["OPS"] >= 3 and scores["LOGISTICS"] >= 3:
        best_role = UNKNOWN
    if scores["OPS"] >= 3 and scores["MAINTENANCE"] >= 3:
        best_role = UNKNOWN

    if return_debug:
        debug = {
            "scores": dict(scores),
            "strong_hits": strong_hits,
            "weak_hits": weak_hits,
            "best_role": best_role,
            "best_score": best_score,
            "second_role": second_role,
            "second_score": second_score,
        }
        return best_role, debug
    return best_role
