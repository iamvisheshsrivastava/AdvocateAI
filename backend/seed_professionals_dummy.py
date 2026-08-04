"""One-off dummy-data seeder for the professionals table.

Populates realistic-but-not-verified lawyer/firm listings across major German
cities and practice areas, including embeddings so the RAG/matching pipeline
in matching_service.py (which filters on `embedding IS NOT NULL`) has data to
work against. This is demo data for a prototype, not verified business
listings.
"""
import json
import random

from db.database import get_db_connection
from services.ai_service import embed_model

random.seed(42)

CITIES = [
    "Berlin", "Hamburg", "Munich", "Frankfurt", "Cologne",
    "Stuttgart", "Dusseldorf", "Leipzig", "Dortmund", "Essen",
]

PRACTICE_AREAS = [
    "Tenant Law", "Employment Law", "Consumer Protection", "Family Law",
    "Civil Litigation", "Criminal Law", "Corporate Law", "Immigration Law",
    "Real Estate Law", "Contract Law",
]

# Real firm names found via web search (approximate, not verified addresses)
KNOWN_FIRMS = [
    ("Gleiss Lutz", "Corporate Law"),
    ("HEUKING", "Corporate Law"),
    ("Luther Rechtsanwaltsgesellschaft", "Corporate Law"),
    ("Hengeler Mueller", "Corporate Law"),
    ("GvW Graf von Westphalen", "Corporate Law"),
    ("CMS Hasche Sigle", "Corporate Law"),
    ("Busse & Miessen", "Civil Litigation"),
    ("Brehm & v. Moers", "Civil Litigation"),
    ("Bueing Mueffelmann & Theye", "Corporate Law"),
    ("Blomstein", "Criminal Law"),
    ("Rechtsanwaelte Woehrle & Schick", "Family Law"),
    ("advomano Rechtsanwaelte", "Employment Law"),
    ("Schlun & Elseven Rechtsanwaelte", "Criminal Law"),
    ("Dr. Wachs Rechtsanwaelte", "Consumer Protection"),
    ("ROSE & PARTNER", "Real Estate Law"),
    ("vpmk Legal Services", "Tenant Law"),
    ("MTR Legal Rechtsanwaelte", "Consumer Protection"),
]

STREETS = [
    "Hauptstrasse", "Bahnhofstrasse", "Friedrichstrasse", "Schillerstrasse",
    "Goethestrasse", "Kaiserstrasse", "Marktplatz", "Poststrasse",
    "Lindenallee", "Rosenweg",
]

SURNAMES = [
    "Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer",
    "Wagner", "Becker", "Hoffmann", "Schulz", "Koch", "Richter",
    "Klein", "Wolf", "Neumann", "Schwarz", "Zimmermann", "Braun",
]


def _random_address(city: str) -> str:
    street = random.choice(STREETS)
    number = random.randint(1, 180)
    postal = random.randint(10000, 99999)
    return f"{street} {number}, {postal} {city}"


def build_records() -> list[dict]:
    records = []

    for name, category in KNOWN_FIRMS:
        city = random.choice(CITIES)
        records.append({
            "name": name,
            "address": _random_address(city),
            "city": city,
            "category": category,
            "rating": round(random.uniform(4.0, 4.9), 1),
            "review_count": random.randint(15, 320),
        })

    # Fill out remaining cities/practice areas with synthetic but plausible entries
    target_total = 80
    while len(records) < target_total:
        surname = random.choice(SURNAMES)
        second = random.choice([s for s in SURNAMES if s != surname])
        city = random.choice(CITIES)
        category = random.choice(PRACTICE_AREAS)
        name = f"Kanzlei {surname} & {second}"
        records.append({
            "name": name,
            "address": _random_address(city),
            "city": city,
            "category": category,
            "rating": round(random.uniform(3.6, 4.9), 1),
            "review_count": random.randint(3, 250),
        })

    return records


def seed_professionals() -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    inserted = 0

    for record in build_records():
        embedding_text = f"{record['name']} - {record['category']} lawyer in {record['city']}, Germany"
        embedding = embed_model.encode(embedding_text)
        embedding_list = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

        cur.execute(
            """
            INSERT INTO professionals (name, address, city, rating, review_count, category, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, address) DO NOTHING
            """,
            (
                record["name"],
                record["address"],
                record["city"],
                record["rating"],
                record["review_count"],
                record["category"],
                json.dumps(embedding_list),
            ),
        )
        inserted += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    return inserted


if __name__ == "__main__":
    count = seed_professionals()
    print(f"Inserted {count} professional records with embeddings.")
