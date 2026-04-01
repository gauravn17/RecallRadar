import csv
import random
from datetime import date, timedelta
from pathlib import Path

BRANDS = [
    "Green Valley",
    "SunBite",
    "FarmNest",
    "TrailJoy",
    "PeakFuel",
    "UrbanHarvest",
    "PureRoot",
    "DailySource",
]

PRODUCT_TEMPLATES = [
    "Organic Spinach",
    "Frozen Dumplings",
    "Greek Yogurt",
    "Protein Shake",
    "Granola Bars",
    "Whole Milk",
    "Fresh Salad Mix",
    "Chicken Nuggets",
]

RECALL_REASONS = [
    "Potential E. coli contamination",
    "Undeclared peanut allergen",
    "Possible metal fragments",
    "Listeria monocytogenes risk",
    "Packaging integrity issue",
]

STATES = ["CA", "TX", "NY", "WA", "OR", "AZ", "NV", "CO", "UT", "ALL"]
LOCATIONS = ["Fridge", "Freezer", "Pantry"]


def generate_synthetic_data(
    recalls_path: Path,
    pantry_path: Path,
    recalls_count: int,
    pantry_count: int,
    seed: int = 42,
) -> tuple[int, int]:
    rng = random.Random(seed)

    today = date.today()
    recalls_path.parent.mkdir(parents=True, exist_ok=True)
    pantry_path.parent.mkdir(parents=True, exist_ok=True)

    with recalls_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["recall_id", "event_date", "product_name", "brand", "reason", "classification", "states"])
        for i in range(recalls_count):
            rid = f"R-SYN-{i:07d}"
            event_date = today - timedelta(days=rng.randint(0, 120))
            product = rng.choice(PRODUCT_TEMPLATES)
            brand = rng.choice(BRANDS)
            reason = rng.choice(RECALL_REASONS)
            classification = rng.choices(["I", "II", "III"], weights=[0.35, 0.45, 0.20], k=1)[0]
            state_vals = "ALL" if rng.random() < 0.12 else ";".join(rng.sample(STATES[:-1], k=rng.randint(2, 4)))
            writer.writerow([rid, event_date.isoformat(), product, brand, reason, classification, state_vals])

    with pantry_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "item_name", "brand", "quantity", "location"])
        for i in range(pantry_count):
            iid = f"P-SYN-{i:07d}"
            product = rng.choice(PRODUCT_TEMPLATES)
            brand = rng.choice(BRANDS)
            quantity = rng.randint(1, 12)
            location = rng.choice(LOCATIONS)
            writer.writerow([iid, product, brand, quantity, location])

    return recalls_count, pantry_count
