import unittest

from recall_radar.matching import classification_weight, compute_match_score, risk_bucket


class MatchingTests(unittest.TestCase):
    def test_classification_weight_mapping(self) -> None:
        self.assertEqual(classification_weight("I"), 1.0)
        self.assertEqual(classification_weight("II"), 0.7)
        self.assertEqual(classification_weight("III"), 0.4)

    def test_compute_match_score_prefers_brand_and_name_overlap(self) -> None:
        item = {"item_id": "P1", "item_name": "Organic Spinach", "brand": "Green Valley"}
        recall = {
            "recall_id": "R1",
            "product_name": "Organic Baby Spinach",
            "brand": "Green Valley",
            "classification": "I",
            "states": "CA;NV",
        }

        score = compute_match_score(item, recall, user_state="CA")
        self.assertGreaterEqual(score.score, 0.6)
        self.assertIn("brand match", score.reasons)

    def test_risk_bucket(self) -> None:
        self.assertEqual(risk_bucket(0.8), "HIGH")
        self.assertEqual(risk_bucket(0.6), "MEDIUM")
        self.assertEqual(risk_bucket(0.4), "LOW")


if __name__ == "__main__":
    unittest.main()
