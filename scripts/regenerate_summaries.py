import sys
import os

# Add parent directory to path to import system_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from system_manager import SystemManager

def regenerate():
    mgr = SystemManager()
    print("🔄 Triggering regeneration of summaries...")
    mgr.backfill_summaries(force=True)

if __name__ == "__main__":
    regenerate()
