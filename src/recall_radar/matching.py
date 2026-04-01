import re
from dataclasses import dataclass

WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class MatchScore:
    item_id: str
    recall_id: str
    score: float
    reasons: list[str]


def _tokens(text: str) -> set[str]:
    return set(WORD_RE.findall((text or "").lower()))


def extract_tokens(text: str) -> set[str]:
    """Public token helper for indexing and blocking strategies."""
    return _tokens(text)


def classification_weight(classification: str) -> float:
    mapping = {"I": 1.0, "II": 0.7, "III": 0.4}
    return mapping.get((classification or "").strip().upper(), 0.5)


def compute_match_score(item: dict, recall: dict, user_state: str = "CA") -> MatchScore:
    reasons: list[str] = []

    item_brand = (item.get("brand") or "").strip().lower()
    recall_brand = (recall.get("brand") or "").strip().lower()
    brand_match = item_brand != "" and item_brand == recall_brand

    item_tokens = _tokens(item.get("item_name") or "")
    recall_tokens = _tokens(recall.get("product_name") or "")
    overlap = len(item_tokens & recall_tokens)
    union = max(1, len(item_tokens | recall_tokens))
    name_similarity = overlap / union

    recall_states = (recall.get("states") or "").upper().split(";")
    state_match = "ALL" in recall_states or user_state.upper() in recall_states

    if brand_match:
        reasons.append("brand match")
    if name_similarity > 0:
        reasons.append(f"name overlap={name_similarity:.2f}")
    if state_match:
        reasons.append("state impacted")

    class_w = classification_weight(recall.get("classification") or "")

    score = 0.0
    score += 0.45 if brand_match else 0.0
    score += min(0.35, name_similarity * 0.5)
    score += 0.1 if state_match else 0.0
    score += 0.1 * class_w

    return MatchScore(
        item_id=item.get("item_id", ""),
        recall_id=recall.get("recall_id", ""),
        score=round(min(score, 1.0), 3),
        reasons=reasons,
    )


def risk_bucket(score: float) -> str:
    if score >= 0.78:
        return "HIGH"
    if score >= 0.58:
        return "MEDIUM"
    return "LOW"
