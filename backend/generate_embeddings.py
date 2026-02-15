import psycopg2
import json
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2") #384 numbers per embedding

# Connect to DB
conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres",
    port=5432
)

cur = conn.cursor()

# Ensure embedding column exists
cur.execute("""
ALTER TABLE professionals
ADD COLUMN IF NOT EXISTS embedding TEXT;
""")
conn.commit()

# Fetch professionals
cur.execute("""
SELECT id, name, category, city, rating, review_count
FROM professionals
WHERE embedding IS NULL
""")
rows = cur.fetchall()

count = 0

for row in rows:
    prof_id, name, category, city, rating, review_count = row

    # Create descriptive text
    text = f"{category} named {name} in {city} with rating {rating} and {review_count} reviews"

    # Generate embedding
    embedding = model.encode(text).tolist()
    embedding_text = json.dumps(embedding)

    # Update DB
    cur.execute(
        "UPDATE professionals SET embedding = %s WHERE id = %s",
        (embedding_text, prof_id)
    )

    count += 1

conn.commit()
cur.close()
conn.close()

print(f"Embeddings generated for {count} professionals.")
