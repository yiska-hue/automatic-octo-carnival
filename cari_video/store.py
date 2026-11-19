"""טבלת התסריטים (CSV). אפשר לפתוח ולערוך אותה באקסל או ב-Google Sheets.

סטטוסים:
  draft      - נוצר אוטומטית, מחכה לבדיקה
  approved   - אושר ע"י אדם, מוכן להפקה
  rendering  - נשלח ל-HeyGen
  done       - הסרטון מוכן והורד
  failed     - ההפקה נכשלה (פרטים בעמודת notes)
"""
import csv
from pathlib import Path

FIELDS = ["id", "topic", "platform", "title", "script", "status", "video_id", "video_url", "file", "notes"]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: (row.get(k) or "") for k in FIELDS} for row in csv.DictReader(f)]


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    # utf-8-sig כדי שאקסל יציג עברית נכון
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})
    tmp.replace(path)


def next_id(rows: list[dict]) -> int:
    ids = [int(r["id"]) for r in rows if r["id"].isdigit()]
    return max(ids, default=0) + 1
