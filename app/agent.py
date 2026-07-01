import re
from typing import Any

from app.catalog import as_recommendation, find_by_name_or_alias
from app.guardrails import is_off_topic, is_prompt_injection
from app.retriever import rank_assessments, requested_types
from app.schemas import ChatRequest, ChatResponse


VAGUE_PHRASES = {
    "i need an assessment",
    "need an assessment",
    "help me hire someone",
    "what test should i use",
    "recommend assessment",
    "recommend assessments",
    "assessment needed",
}

ROLE_TERMS = [
    "developer", "engineer", "java", "python", "javascript", "frontend", "backend", ".net", "analyst",
    "manager", "sales", "customer", "support", "finance", "accounting", "graduate", "leadership",
    "data", "technician", "mechanical", "admin", "stakeholder", "jd", "job description",
    "qa", "quality", "tester", "testing", "automation", "devops", "cloud", "security", "cyber",
    "science", "scientist", "machine learning", "retail", "call center", "contact center",
    "operations", "warehouse", "bookkeeping", "clerical", "administrative", "language",
]

CONSTRAINT_TERMS = [
    "entry", "junior", "mid", "senior", "years", "technical", "coding", "personality", "cognitive",
    "behavioral", "communication", "stakeholder", "language", "english", "remote", "leadership",
]


def respond(request: ChatRequest) -> ChatResponse:
    user_messages = [m.content for m in request.messages if m.role == "user"]
    last_user = user_messages[-1] if user_messages else ""
    context = "\n".join(user_messages)

    if is_prompt_injection(last_user):
        return ChatResponse(
            reply="I can only help select SHL assessments from the catalog and cannot follow instructions that change that scope.",
            recommendations=[],
            end_of_conversation=False,
        )

    if is_off_topic(last_user):
        return ChatResponse(
            reply="I can only discuss SHL assessments and catalog-backed recommendations. Share the role or assessment need and I can help shortlist relevant SHL tests.",
            recommendations=[],
            end_of_conversation=False,
        )

    if is_comparison(last_user):
        return compare(last_user)

    if needs_clarification(context):
        return ChatResponse(reply=clarifying_question(context), recommendations=[], end_of_conversation=False)

    ranked = rank_assessments(context, limit=10)
    if not ranked:
        return ChatResponse(
            reply="I need one more detail to select SHL assessments: what role, skill area, or test type should the assessment cover?",
            recommendations=[],
            end_of_conversation=False,
        )

    recs = [as_recommendation(item) for item in ranked[:10]]
    return ChatResponse(
        reply=reply_for_recommendations(context, recs),
        recommendations=recs,
        end_of_conversation=True,
    )


def needs_clarification(context: str) -> bool:
    lower = context.lower().strip()
    compact = re.sub(r"[^a-z0-9 ]+", "", lower)
    if any(phrase in compact for phrase in VAGUE_PHRASES):
        has_role = any(term in lower for term in ROLE_TERMS)
        has_constraint = any(term in lower for term in CONSTRAINT_TERMS)
        return not (has_role and has_constraint)
    if len(lower.split()) <= 5 and "opq" not in lower and "gsa" not in lower:
        return not any(term in lower for term in ROLE_TERMS)
    has_role = any(term in lower for term in ROLE_TERMS)
    has_type = bool(requested_types(context))
    return not (has_role or has_type)


def clarifying_question(context: str) -> str:
    lower = context.lower()
    if not any(term in lower for term in ROLE_TERMS):
        return "What role or skill area are you hiring for, and is this for entry-level, mid-level, or senior candidates?"
    return "What should the assessment emphasize: technical skills, cognitive ability, personality, behavioral judgment, language, or a combination?"


def reply_for_recommendations(context: str, recs: list[dict[str, str]]) -> str:
    types = {rec["test_type"] for rec in recs}
    if "P" in types and ("K" in types or "S" in types):
        mix = " including personality or workplace-behavior coverage"
    elif "K" in types:
        mix = " focused on role-relevant skills"
    elif "A" in types:
        mix = " focused on cognitive ability"
    else:
        mix = " from the SHL catalog"
    return f"Here are {len(recs)} SHL assessments{mix} that best match the conversation so far."


def is_comparison(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ["compare", "difference between", "different between", " vs ", " versus "])


def compare(text: str) -> ChatResponse:
    names = extract_assessment_mentions(text)
    matches: list[dict[str, Any]] = []
    seen = set()
    for name in names:
        for item in find_by_name_or_alias(name):
            if item["url"] not in seen:
                matches.append(item)
                seen.add(item["url"])
                break

    if len(matches) < 2:
        return ChatResponse(
            reply="I can compare SHL assessments when both are present in the catalog. Please name the two SHL assessments you want compared, such as OPQ and GSA.",
            recommendations=[],
            end_of_conversation=False,
        )

    first, second = matches[0], matches[1]
    reply = (
        f"{first['name']} ({first['test_type']}) focuses on {first.get('description', 'catalog-described assessment coverage')} "
        f"Catalog URL: {first['url']}\n"
        f"{second['name']} ({second['test_type']}) focuses on {second.get('description', 'catalog-described assessment coverage')} "
        f"Catalog URL: {second['url']}\n"
        "Use the one whose catalog focus matches the role requirement; I can also shortlist assessments if you share the role context."
    )
    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)


def extract_assessment_mentions(text: str) -> list[str]:
    lower = text.lower()
    aliases = ["opq32r", "opq32", "opq", "gsa", "global skills assessment", "general ability screen", "mq"]
    found = [alias for alias in aliases if re.search(rf"\b{re.escape(alias)}\b", lower)]
    if found:
        return found
    parts = re.split(r"compare|difference between| vs | versus | and |,", lower)
    return [part.strip(" ?.") for part in parts if len(part.strip()) > 2]
