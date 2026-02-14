from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres",
    port=5432
)

# Get all artists
@app.get("/artists")
def get_artists():
    cur = conn.cursor()
    cur.execute("SELECT id, name, genre, monthly_listeners, popularity FROM artists LIMIT 50")
    rows = cur.fetchall()
    cur.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "name": r[1],
            "genre": r[2],
            "monthly_listeners": r[3],
            "popularity": r[4]
        })

    return result


# Simple recommender: similar artists
@app.get("/recommend/{artist_id}")
def recommend(artist_id: int):
    cur = conn.cursor()

    query = """
    SELECT id, name, genre, popularity
    FROM artists
    WHERE genre = (
        SELECT genre FROM artists WHERE id = %s
    )
    AND id != %s
    ORDER BY ABS(popularity - (
        SELECT popularity FROM artists WHERE id = %s
    ))
    LIMIT 10;
    """

    cur.execute(query, (artist_id, artist_id, artist_id))
    rows = cur.fetchall()
    cur.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "name": r[1],
            "genre": r[2],
            "popularity": r[3]
        })

    return result
