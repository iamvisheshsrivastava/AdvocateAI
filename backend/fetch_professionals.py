import psycopg2
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Major German cities
CITIES = [
    "Berlin", "Hamburg", "Munich", "Frankfurt", "Cologne",
    "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund",
    "Essen", "Bremen", "Hanover", "Nuremberg",
    "Dresden", "Bochum", "Wuppertal", "Bielefeld",
    "Bonn", "Münster", "Karlsruhe"
]

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres",
    port=5432
)


def insert_places(places, city):
    cur = conn.cursor()
    count = 0

    for place in places:
        name = place.get("name")
        address = place.get("formatted_address")
        rating = place.get("rating", 0)
        review_count = place.get("user_ratings_total", 0)

        cur.execute("""
            INSERT INTO professionals (name, address, city, rating, review_count, category)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, address) DO NOTHING;
        """, (name, address, city, rating, review_count, "lawyer"))

        count += 1

    conn.commit()
    cur.close()
    return count


def fetch_city_lawyers(city):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    params = {
        "query": f"lawyers in {city}",
        "key": API_KEY
    }

    total_inserted = 0

    # First request
    response = requests.get(url, params=params)
    data = response.json()

    total_inserted += insert_places(data.get("results", []), city)

    # Pagination (up to 2 more pages)
    for _ in range(2):
        next_token = data.get("next_page_token")
        if not next_token:
            break

        time.sleep(3)  # Required wait for token activation

        params = {
            "pagetoken": next_token,
            "key": API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        total_inserted += insert_places(data.get("results", []), city)

    print(f"{total_inserted} professionals processed for {city}")


def run_full_ingestion():
    for city in CITIES:
        try:
            fetch_city_lawyers(city)
            time.sleep(1) 
        except Exception as e:
            print(f"Error in city {city}: {e}")


if __name__ == "__main__":
    run_full_ingestion()
    conn.close()
