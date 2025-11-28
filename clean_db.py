import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
SPACE_X = "tum_space_x"
SPACE_R = "tum_space_r"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

print(f"Deleting collection {SPACE_X}...")
client.delete_collection(collection_name=SPACE_X)
print(f"Deleted {SPACE_X}")

print(f"Deleting collection {SPACE_R}...")
client.delete_collection(collection_name=SPACE_R)
print(f"Deleted {SPACE_R}")

print("✅ Database cleaned. Restart server to repopulate.")
