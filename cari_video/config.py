"""הגדרות הכלי. כל הערכים נקראים ממשתני סביבה (או מקובץ .env)."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    heygen_api_key: str = os.environ.get("HEYGEN_API_KEY", "")
    avatar_id: str = os.environ.get("HEYGEN_AVATAR_ID", "")
    voice_id: str = os.environ.get("HEYGEN_VOICE_ID", "")
    # "vertical" = 1080x1920 (רילס/טיקטוק/סטטוס), "horizontal" = 1920x1080 (יוטיוב/אתר)
    orientation: str = os.environ.get("VIDEO_ORIENTATION", "vertical")
    background_color: str = os.environ.get("VIDEO_BACKGROUND", "#FFFFFF")
    captions: bool = os.environ.get("VIDEO_CAPTIONS", "true").lower() == "true"
    claude_model: str = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")

    scripts_csv: Path = ROOT / "data" / "scripts.csv"
    topics_csv: Path = ROOT / "data" / "topics.csv"
    brand_guide: Path = ROOT / "data" / "brand_guide.md"
    boss_samples: Path = ROOT / "data" / "boss_samples.md"
    output_dir: Path = ROOT / "output"


settings = Settings()
