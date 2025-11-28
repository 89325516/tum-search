import sys
import os

# Add parent directory to path to import system_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from system_manager import SystemManager, SPACE_X

def clear_x():
    mgr = SystemManager()
    print(f"🗑️ Clearing collection: {SPACE_X}...")
    mgr.client.delete_collection(SPACE_X)
    print(f"✅ Collection {SPACE_X} deleted.")
    mgr._init_collections()
    mgr._ensure_indices()
    print(f"✅ Collection {SPACE_X} re-initialized.")

if __name__ == "__main__":
    clear_x()
