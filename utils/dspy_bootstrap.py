import os
from pathlib import Path


def ensure_dspy_cache_dir() -> Path:
    """Force DSPy to use a writable cache directory."""

    raw = os.environ.get("DSPY_CACHEDIR", "").strip()
    if raw:
        cache_dir = Path(raw).expanduser()
    else:
        repo_root = Path(__file__).resolve().parents[1]
        cache_dir = repo_root / "storage" / "dspy_cache"
        os.environ["DSPY_CACHEDIR"] = str(cache_dir)

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
