"""כלי שורת פקודה להפקת סרטוני האווטאר של קארי.

  python -m cari_video write     # נושאים מ-data/topics.csv -> תסריטי טיוטה ב-data/scripts.csv
  python -m cari_video add "נושא" --platform אינסטגרם   # תסריט לנושא אחד
  (פותחים את data/scripts.csv, עוברים על התסריטים ומשנים status ל-approved)
  python -m cari_video render    # מפיק ב-HeyGen רק תסריטים שאושרו ומוריד ל-output/
  python -m cari_video status    # סיכום מצב
  python -m cari_video avatars   # רשימת האווטארים והקולות בחשבון HeyGen
"""
import argparse
import csv
import re
import sys

from . import store
from .config import settings


def _slug(text: str) -> str:
    return re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_")[:40] or "video"


def _add_drafts(rows, topic, platform, count):
    from .scriptwriter import write_scripts
    for s in write_scripts(topic, platform, count):
        rows.append({"id": str(store.next_id(rows)), "topic": topic, "platform": platform,
                     "title": s.title, "script": s.script, "status": "draft"})
        print(f"  + #{rows[-1]['id']} {s.title}")


def cmd_write(args):
    if not settings.topics_csv.exists():
        sys.exit(f"לא נמצא {settings.topics_csv}")
    rows = store.load(settings.scripts_csv)
    done_topics = {r["topic"] for r in rows}
    with settings.topics_csv.open(encoding="utf-8-sig", newline="") as f:
        topics = list(csv.DictReader(f))
    for t in topics:
        topic = (t.get("topic") or "").strip()
        if not topic or (topic in done_topics and not args.force):
            continue
        print(f"כותב: {topic}")
        _add_drafts(rows, topic, (t.get("platform") or "").strip(), int(t.get("versions") or 1))
        store.save(settings.scripts_csv, rows)  # שומר אחרי כל נושא
    print(f"\nהתסריטים נמצאים ב-{settings.scripts_csv}. אשרו אותם (status=approved) לפני render.")


def cmd_add(args):
    rows = store.load(settings.scripts_csv)
    _add_drafts(rows, args.topic, args.platform, args.versions)
    store.save(settings.scripts_csv, rows)


def cmd_render(args):
    from .heygen import HeyGen, HeyGenError
    if not settings.avatar_id or not settings.voice_id:
        sys.exit("חסרים HEYGEN_AVATAR_ID או HEYGEN_VOICE_ID בקובץ .env (אפשר למצוא אותם עם: python -m cari_video avatars)")
    hg = HeyGen(settings.heygen_api_key)
    rows = store.load(settings.scripts_csv)
    todo = [r for r in rows if r["status"] in ("approved", "rendering")]
    if args.id:
        todo = [r for r in todo if r["id"] in args.id]
    if not todo:
        print("אין תסריטים במצב approved. צריך לאשר תסריטים ב-data/scripts.csv קודם.")
        return
    for r in todo:
        try:
            if r["status"] == "approved" or not r["video_id"]:
                r["video_id"] = hg.create_video(
                    text=r["script"], avatar_id=settings.avatar_id, voice_id=settings.voice_id,
                    title=f"Cari #{r['id']} {r['title']}", orientation=settings.orientation,
                    background=settings.background_color, captions=settings.captions)
                r["status"] = "rendering"
                store.save(settings.scripts_csv, rows)
                print(f"#{r['id']} נשלח להפקה ({r['video_id']})")
            if args.no_wait:
                continue
            url = hg.wait(r["video_id"])
            dest = settings.output_dir / f"{int(r['id']):03d}_{_slug(r['title'])}.mp4"
            hg.download(url, dest)
            r.update(status="done", video_url=url, file=str(dest.relative_to(settings.output_dir.parent)), notes="")
            print(f"#{r['id']} מוכן: {dest}")
        except HeyGenError as e:
            r.update(status="failed", notes=str(e)[:500])
            print(f"#{r['id']} נכשל: {e}")
        store.save(settings.scripts_csv, rows)


def cmd_status(args):
    rows = store.load(settings.scripts_csv)
    counts = {}
    for r in rows:
        counts[r["status"] or "?"] = counts.get(r["status"] or "?", 0) + 1
        print(f"#{r['id']:>3} [{r['status']:<9}] {r['title']}")
    print("\n" + ", ".join(f"{k}: {v}" for k, v in counts.items()) if rows else "אין עדיין תסריטים.")


def cmd_avatars(args):
    from .heygen import HeyGen
    hg = HeyGen(settings.heygen_api_key)
    print("אווטארים:")
    for a in hg.list_avatars():
        print(f"  {a.get('avatar_id')}  {a.get('avatar_name')}")
    print("\nקולות (עברית):")
    for v in hg.list_voices():
        if "hebrew" in (v.get("language") or "").lower() or v.get("is_cloned") or args.all:
            print(f"  {v.get('voice_id')}  {v.get('name')}  ({v.get('language')})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cari_video", description="הפקת סרטוני אווטאר לקארי")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="תסריטים לכל הנושאים ב-topics.csv")
    w.add_argument("--force", action="store_true", help="כתוב מחדש גם לנושאים שכבר יש להם תסריט")
    w.set_defaults(func=cmd_write)

    a = sub.add_parser("add", help="תסריט לנושא בודד")
    a.add_argument("topic")
    a.add_argument("--platform", default="")
    a.add_argument("--versions", type=int, default=1)
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("render", help="הפקת התסריטים שאושרו ב-HeyGen")
    r.add_argument("--id", nargs="*", help="רק מספרי תסריט מסוימים")
    r.add_argument("--no-wait", action="store_true", help="שלח להפקה בלי לחכות. הרצה חוזרת של render תוריד את מה שמוכן")
    r.set_defaults(func=cmd_render)

    sub.add_parser("status", help="סיכום מצב").set_defaults(func=cmd_status)

    av = sub.add_parser("avatars", help="רשימת אווטארים וקולות")
    av.add_argument("--all", action="store_true", help="הצג את כל הקולות, לא רק עברית ומשוכפלים")
    av.set_defaults(func=cmd_avatars)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
