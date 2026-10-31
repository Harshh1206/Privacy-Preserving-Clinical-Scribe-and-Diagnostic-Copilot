from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.store import get_store


if __name__ == "__main__":
    get_store().seed()
    print("Seed data is loaded (existing records were preserved or matched by stable ID).")
