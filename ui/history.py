"""Report history  persist to / load from a local JSON file."""

import json
import uuid
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path("report_history.json")
MAX_HISTORY = 30


def load() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def save(history: list[dict]) -> None:
    try:
        HISTORY_FILE.write_text(json.dumps(history, indent=2))
    except Exception:
        pass


def add(topic: str, report: str) -> None:
    history = load()
    history.insert(
        0,
        {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "report": report,
            "created_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        },
    )
    save(history[:MAX_HISTORY])


def clear() -> None:
    save([])
