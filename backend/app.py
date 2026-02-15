from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2

app = FastAPI()
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres",
    port=5432
)

# Request model
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
def login(data: LoginRequest):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, email FROM users WHERE email = %s AND password = %s",
        (data.email, data.password)
    )
    user = cur.fetchone()
    cur.close()

    if user:
        return {"success": True, "user_id": user[0], "email": user[1]}
    else:
        return {"success": False}


class ChatRequest(BaseModel):
    message: str

from sentence_transformers import SentenceTransformer
import json

# load embedding model once
embed_model = SentenceTransformer("all-MiniLM-L6-v2")


@app.post("/chat")
def chat(data: ChatRequest):
    try:
        # 1. Convert user message to embedding
        user_embedding = embed_model.encode(data.message).tolist()

        # 2. Fetch all professionals and compute similarity
        cur = conn.cursor()
        cur.execute("SELECT name, address, city, rating, review_count, embedding FROM professionals WHERE embedding IS NOT NULL")
        rows = cur.fetchall()
        cur.close()

        import numpy as np

        best_matches = []

        for row in rows:
            name, address, city, rating, reviews, emb = row
            db_embedding = np.array(json.loads(emb))
            score = np.dot(user_embedding, db_embedding)

            best_matches.append((score, name, city, rating, reviews))

        # sort by similarity
        best_matches.sort(reverse=True, key=lambda x: x[0])
        top_results = best_matches[:3]

        # 3. Build context for LLM
        if top_results:
            context = "Top matching professionals:\n"
            for _, name, city, rating, reviews in top_results:
                context += f"- {name} in {city}, rating {rating} ({reviews} reviews)\n"

            final_prompt = f"""
User question: {data.message}

Use the following professionals to answer:
{context}

Respond naturally and recommend the best options.
"""
        else:
            final_prompt = data.message

        # 4. Call Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": final_prompt}
                    ]
                }
            ]
        }

        response = requests.post(url, json=payload)
        result = response.json()

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return {"response": text}

    except Exception as e:
        print("ERROR:", e)
        return {"response": "Sorry, I couldn’t generate a response."}


@app.get("/watchlist/{user_id}")
def get_watchlist(user_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.city, p.category, p.rating, p.review_count
        FROM watchlist w
        JOIN professionals p ON w.professional_id = p.id
        WHERE w.user_id = %s
        ORDER BY p.rating DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()

    result = [
        {
            "id": r[0],
            "name": r[1],
            "city": r[2],
            "category": r[3],
            "rating": r[4],
            "reviews": r[5],
        }
        for r in rows
    ]

    return result


@app.get("/professionals/{user_id}")
def get_professionals(user_id: int):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, city, rating, review_count
        FROM professionals
        WHERE id NOT IN (
            SELECT professional_id
            FROM watchlist
            WHERE user_id = %s
        )
        ORDER BY rating DESC
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()

    result = [
        {
            "id": r[0],
            "name": r[1],
            "city": r[2],
            "rating": r[3],
            "reviews": r[4],
        }
        for r in rows
    ]

    return result


class WatchlistRequest(BaseModel):
    user_id: int
    professional_ids: list[int]


@app.post("/watchlist/add")
def add_to_watchlist(data: WatchlistRequest):
    cur = conn.cursor()

    for pid in data.professional_ids:
        cur.execute("""
            INSERT INTO watchlist (user_id, professional_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, professional_id) DO NOTHING
        """, (data.user_id, pid))

    conn.commit()
    cur.close()

    return {"success": True}
