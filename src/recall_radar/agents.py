from dataclasses import dataclass
from datetime import datetime

from .matching import MatchScore, compute_match_score, extract_tokens, risk_bucket


@dataclass
class DetectionAgent:
    threshold: float = 0.52

    def run(self, pantry_items: list[dict], recalls: list[dict], user_state: str) -> list[MatchScore]:
        recall_by_id = {r["recall_id"]: r for r in recalls}
        recalls_by_brand: dict[str, set[str]] = {}
        recalls_by_token: dict[str, set[str]] = {}

        for recall in recalls:
            rid = recall["recall_id"]
            brand = (recall.get("brand") or "").strip().lower()
            if brand:
                recalls_by_brand.setdefault(brand, set()).add(rid)
            for token in extract_tokens(recall.get("product_name") or ""):
                if len(token) >= 3:
                    recalls_by_token.setdefault(token, set()).add(rid)

        total_candidates = 0
        total_comparisons = 0
        hits: list[MatchScore] = []
        for item in pantry_items:
            brand = (item.get("brand") or "").strip().lower()
            candidate_ids: set[str] = set()
            if brand:
                candidate_ids.update(recalls_by_brand.get(brand, set()))

            for token in extract_tokens(item.get("item_name") or ""):
                if len(token) >= 3:
                    candidate_ids.update(recalls_by_token.get(token, set()))

            total_candidates += len(candidate_ids)
            for recall_id in candidate_ids:
                recall = recall_by_id[recall_id]
                score = compute_match_score(item, recall, user_state=user_state)
                total_comparisons += 1
                if score.score >= self.threshold:
                    hits.append(score)

        self.last_stats = {
            "pantry_items": len(pantry_items),
            "recalls": len(recalls),
            "candidate_pairs": total_candidates,
            "scored_pairs": total_comparisons,
            "cartesian_pairs": len(pantry_items) * len(recalls),
        }
        hits.sort(key=lambda x: x.score, reverse=True)
        return hits


@dataclass
class TriageAgent:
    def run(self, matches: list[MatchScore]) -> dict[str, list[MatchScore]]:
        grouped: dict[str, list[MatchScore]] = {"HIGH": [], "MEDIUM": [], "LOW": []}
        for match in matches:
            grouped[risk_bucket(match.score)].append(match)
        return grouped


@dataclass
class ActionPlannerAgent:
    max_actions_per_bucket: int = 30

    def run(self, triaged: dict[str, list[MatchScore]], pantry_by_id: dict, recalls_by_id: dict) -> list[str]:
        actions: list[str] = []

        def _line(prefix: str, ms: MatchScore) -> str:
            item = pantry_by_id[ms.item_id]
            rec = recalls_by_id[ms.recall_id]
            return (
                f"{prefix}: {item['item_name']} ({item.get('brand', 'Unknown')}) -> "
                f"{rec['product_name']} [{rec['classification']}], score={ms.score}"
            )

        best_by_item: dict[str, MatchScore] = {}
        for bucket in ["HIGH", "MEDIUM", "LOW"]:
            for ms in triaged[bucket]:
                current = best_by_item.get(ms.item_id)
                if current is None or ms.score > current.score:
                    best_by_item[ms.item_id] = ms

        grouped_best: dict[str, list[MatchScore]] = {"HIGH": [], "MEDIUM": [], "LOW": []}
        for ms in best_by_item.values():
            grouped_best[risk_bucket(ms.score)].append(ms)

        for bucket in grouped_best:
            grouped_best[bucket].sort(key=lambda x: x.score, reverse=True)

        for ms in grouped_best["HIGH"][: self.max_actions_per_bucket]:
            actions.append(_line("DISCARD + REFUND", ms))
        for ms in grouped_best["MEDIUM"][: self.max_actions_per_bucket]:
            actions.append(_line("VERIFY LOT #", ms))
        for ms in grouped_best["LOW"][: self.max_actions_per_bucket]:
            actions.append(_line("MONITOR", ms))

        if not actions:
            actions.append("No likely impacted items found. Continue normal monitoring.")

        actions.append(
            f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by RecallRadar multi-agent pipeline."
        )
        return actions
