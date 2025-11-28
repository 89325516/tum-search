import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
SPACE_X = "tum_space_x"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

target_url = "https://www.tum-venture-labs.de/"

print(f"Checking for URL: {target_url} in {SPACE_X}...")

try:
    # Use the same filtering logic as the server
    hits = client.scroll(
        collection_name=SPACE_X,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="url",
                    match=models.MatchValue(value=target_url)
                )
            ]
        ),
        limit=1
    )[0]

    if hits:
        print(f"✅ Found! ID: {hits[0].id}")
        print(f"   Payload: {hits[0].payload}")
    else:
        print("❌ Not found.")

except Exception as e:
    print(f"Error querying Qdrant: {e}")
