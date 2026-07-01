import math
import re
from collections import Counter
from typing import Any

from app.catalog import load_catalog


TOKEN_RE = re.compile(r"[a-zA-Z0-9+#.]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "for", "from", "has", "have", "here", "hiring",
    "hire", "i", "need", "needs", "please", "recommend", "select", "someone", "who",
    "in", "is", "it", "job", "must", "of", "on", "or", "role", "roles", "that", "the", "this",
    "to", "with", "works", "description", "candidate", "candidates", "assessment", "assessments",
}

ROLE_SYNONYMS = {
    "developer": ["software engineer", "programming", "coding", "technical"],
    "engineer": ["technical", "problem solving"],
    "java": ["java developer", "backend"],
    "python": ["programming", "data science", "backend"],
    "javascript": ["frontend", "web", "node", "typescript"],
    "frontend": ["javascript", "html", "css", "web"],
    "front": ["frontend", "javascript", "html", "css", "web"],
    "analyst": ["data", "excel", "sql", "numerical"],
    "finance": ["accounting", "excel", "numerical", "financial analysis"],
    "accounting": ["bookkeeping", "accounts payable", "accounts receivable", "finance"],
    "manager": ["management", "leadership", "situational judgement", "personality"],
    "sales": ["customer", "persuasion", "business development"],
    "support": ["customer service", "communication", "contact center"],
    "qa": ["quality assurance", "testing", "selenium", "automation"],
    "tester": ["qa", "quality assurance", "selenium", "automation"],
    "testing": ["qa", "quality assurance", "selenium", "automation"],
    "automation": ["selenium", "qa", "testing"],
    "devops": ["cloud", "docker", "kubernetes", "ci/cd", "deployment"],
    "cloud": ["aws", "azure", "devops", "infrastructure"],
    "security": ["cyber", "network", "risk"],
    "cyber": ["security", "network", "risk"],
    "scientist": ["data science", "machine learning", "python", "statistics"],
    "retail": ["customer service", "sales", "service"],
    "warehouse": ["safety", "operations", "dependability"],
    "stakeholder": ["communication", "collaboration", "behavioral", "workplace"],
    "personality": ["opq", "mq", "workplace behavior"],
    "cognitive": ["reasoning", "ability", "verify"],
}

TYPE_TERMS = {
    "K": ["technical", "skill", "knowledge", "coding", "programming", "java", "python", "sql", "excel"],
    "P": ["personality", "behavior", "motivation", "opq", "mq", "leadership"],
    "A": ["cognitive", "ability", "reasoning", "numerical", "verbal", "inductive", "problem solving"],
    "S": ["situational", "judgement", "judgment", "behavioral", "communication", "customer", "stakeholder", "simulation"],
    "L": ["language", "english"],
}

TECH_FAMILIES = {
    "java": {"java", "spring", "hibernate", "j2ee"},
    "python": {"python", "django"},
    "javascript": {"javascript", "typescript", "react", "reactjs", "angular", "node", "node.js", "html", "css"},
    "react": {"react", "reactjs", "javascript", "typescript", "frontend"},
    "angular": {"angular", "javascript", "typescript", "frontend"},
    ".net": {".net", "dotnet", "c#", "microsoft"},
    "c#": {"c#", "c", ".net", "dotnet", "microsoft"},
    "c++": {"c++", "cpp"},
    "sql": {"sql", "database"},
    "aws": {"aws", "cloud"},
    "azure": {"azure", "cloud", "microsoft"},
}
CONFLICT_TECH_TERMS = set().union(*TECH_FAMILIES.values())


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_RE.findall(text):
        normalized = token.lower()
        if normalized in STOPWORDS:
            continue
        if len(normalized) == 1 and normalized not in {"r"}:
            continue
        tokens.append(normalized)
    return tokens


def expand_query(text: str) -> str:
    tokens = tokenize(text)
    expansions: list[str] = []
    for token in tokens:
        expansions.extend(ROLE_SYNONYMS.get(token, []))
    return " ".join([text, *expansions])


def requested_types(text: str) -> set[str]:
    lower = text.lower()
    types = set()
    for test_type, terms in TYPE_TERMS.items():
        if any(term in lower for term in terms):
            types.add(test_type)
    return types


def requested_tech_families(text: str) -> list[set[str]]:
    tokens = set(tokenize(text))
    lower = text.lower()
    families = []
    for trigger, family in TECH_FAMILIES.items():
        if trigger in tokens or trigger in lower:
            families.append(family)
    return families


def rank_assessments(context: str, limit: int = 10) -> list[dict[str, Any]]:
    catalog = load_catalog()
    expanded = expand_query(context)
    query_tokens = tokenize(expanded)
    counts = Counter(query_tokens)
    wanted_types = requested_types(context)
    wanted_tech = requested_tech_families(context)
    results: list[tuple[float, dict[str, Any]]] = []

    for item in catalog:
        search_text = item["search_text"]
        search_tokens = set(tokenize(search_text))
        name_tokens = set(tokenize(item["name"]))
        score = 0.0
        for token, count in counts.items():
            if token in search_tokens:
                score += 1.0 + math.log(count + 1)
            if token in name_tokens:
                score += 2.5
        if wanted_types and item["test_type"] in wanted_types:
            score += 4.0
        if wanted_tech and item["test_type"] == "K":
            matches_requested_tech = any(search_tokens & family for family in wanted_tech)
            has_other_tech = bool(search_tokens & CONFLICT_TECH_TERMS)
            if matches_requested_tech:
                score += 3.0
            elif has_other_tech:
                score -= 3.0
        if "stakeholder" in context.lower() and item["test_type"] in {"P", "S"}:
            score += 2.5
        if "mid" in context.lower() and any(t in search_text for t in ["mid-level", "experienced"]):
            score += 1.0
        if score > 0:
            results.append((score, item))

    results.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    if not results:
        return []

    return [item for _, item in results[:limit]]
