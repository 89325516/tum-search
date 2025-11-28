import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
SPACE_R = "tum_space_r"
SPACE_X = "tum_space_x"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def inspect_collection(name):
    print(f"\n--- Inspecting Collection: {name} ---")
    try:
        count = client.count(collection_name=name).count
        print(f"Total Items: {count}")
        
        if count > 0:
            points, _ = client.scroll(
                collection_name=name,
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            for p in points:
                print(f"ID: {p.id}")
                print(f"Payload: {p.payload}")
                print("-" * 20)
    except Exception as e:
        print(f"Error inspecting {name}: {e}")

if __name__ == "__main__":
    inspect_collection(SPACE_R)
    inspect_collection(SPACE_X)
