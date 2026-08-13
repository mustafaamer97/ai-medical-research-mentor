from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PERSISTENCE_FILE = DATA_DIR / "research_project.json"

APP_TITLE = "AI Medical Research Mentor & Co-Pilot"
APP_VERSION = "1.0.0"
