"""כתיבת תסריטים בסגנון של הבוס בעזרת Claude."""
import anthropic
from pydantic import BaseModel, Field

from .config import settings

SYSTEM_PROMPT = """אתה כותב תסריטים לסרטונים קצרים של חברת "קארי" (Cari), חברת ייעוץ וליווי ברכישת רכב וליסינג.
את הסרטונים מציג אווטאר דיגיטלי של מנהל החברה, שהסכים לכך, והוא מדבר ישירות למצלמה.

כללי כתיבה:
- עברית מדוברת וטבעית, כמו שאדם מדבר, לא כמו מודעה. משפטים קצרים.
- פתיחה חזקה ב-3 השניות הראשונות: שאלה, טעות נפוצה או מספר מפתיע.
- רעיון אחד מרכזי בכל סרטון. בלי רשימות ארוכות.
- סיום עם קריאה לפעולה רכה ולא אגרסיבית.
- כתוב רק את מה שנאמר בקול: בלי הוראות במה, בלי אימוג'ים ובלי סימני markdown.
- אל תמציא מחירים, נתונים, מבצעים, שמות לקוחות או הבטחות. אם צריך מספר, השתמש בדוגמה כללית ("נגיד רכב ב-80 אלף").
- בלי ייעוץ משפטי או ביטוחי מחייב, ובלי השמצה של חברות או מותגים.
- אורך: עד כ-130 מילים לסרטון קצר (כ-45-60 שניות), אלא אם התבקש אחרת.

להלן מדריך המותג וערכי החברה:
<brand_guide>
{brand_guide}
</brand_guide>

להלן דוגמאות לאופן שבו המנהל מדבר. חקה את הטון, את אוצר המילים ואת הקצב שלו:
<boss_samples>
{boss_samples}
</boss_samples>
"""


class Script(BaseModel):
    title: str = Field(description="כותרת פנימית קצרה לסרטון")
    script: str = Field(description="הטקסט המלא שהאווטאר יקריא")


class ScriptBatch(BaseModel):
    scripts: list[Script]


def _read(path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else "(לא סופק)"


def write_scripts(topic: str, platform: str, count: int = 1, client: anthropic.Anthropic | None = None) -> list[Script]:
    client = client or anthropic.Anthropic()
    system = SYSTEM_PROMPT.format(
        brand_guide=_read(settings.brand_guide),
        boss_samples=_read(settings.boss_samples),
    )
    user = (
        f"כתוב {count} גרסאות שונות של תסריט לסרטון.\n"
        f"נושא: {topic}\n"
        f"פלטפורמה: {platform or 'כללי'}"
    )
    response = client.messages.parse(
        model=settings.claude_model,
        max_tokens=16000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=ScriptBatch,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude סירב לכתוב תסריט לנושא: {topic}")
    if response.parsed_output is None:
        raise RuntimeError(f"לא התקבל תסריט תקין לנושא: {topic} (stop_reason={response.stop_reason})")
    return response.parsed_output.scripts
