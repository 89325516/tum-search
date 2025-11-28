import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    print("❌ Error: QDRANT_URL or QDRANT_API_KEY not found in environment variables.")
    exit(1)

print(f"Checking connection to: {QDRANT_URL}")

try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    collections = client.get_collections()
    print("✅ Successfully connected to Qdrant Cloud!")
    print(f"Collections: {[c.name for c in collections.collections]}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)
