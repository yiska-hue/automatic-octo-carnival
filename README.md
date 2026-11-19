# מפעל הסרטונים של קארי: אווטאר של המנהל

הכלי כותב תסריטים בסגנון של המנהל בעזרת Claude. אחרי שאדם מאשר אותם, הוא שולח אותם להפקה באווטאר של המנהל ב-HeyGen ומוריד את הסרטונים המוכנים.

```
topics.csv  ──write──▶  scripts.csv (draft)  ──אישור ידני──▶  approved  ──render──▶  output/*.mp4
```

> **כלל ברזל:** שום סרטון לא מופק בלי שאדם קרא ואישר את התסריט. הכלי מפיק רק שורות שה-status שלהן `approved`.

## הקמה חד-פעמית

### 1. האווטאר ב-HeyGen (המנהל עושה את זה בעצמו)
1. פותחים חשבון ב-[HeyGen](https://www.heygen.com). כדי לקבל גישת API צריך מנוי מתאים.
2. **Avatars → Create Avatar → Digital Twin.** המנהל מקליט 2 עד 5 דקות של וידאו מול המצלמה, בתאורה טובה, על רקע נקי, ומדבר בטבעיות.
3. המנהל מקליט את **סרטון ההסכמה** ש-HeyGen מבקשת. בלי ההקלטה הזו האווטאר לא יאושר.
4. לקול: משתמשים בקול המשוכפל שנוצר עם האווטאר, או משכפלים קול ב-**Voices → Clone Voice**.
5. **Settings → API** ומעתיקים את ה-API key.

### 2. התקנה
```bash
pip install -r requirements.txt
cp .env.example .env        # ממלאים את ANTHROPIC_API_KEY ואת HEYGEN_API_KEY
python -m cari_video avatars   # מציג את ה-avatar_id ואת ה-voice_id
```
מעתיקים את המזהים של המנהל ל-`HEYGEN_AVATAR_ID` ול-`HEYGEN_VOICE_ID` בקובץ `.env`.

### 3. ללמד את הכלי לדבר כמו המנהל
- `data/brand_guide.md` כבר מכיל את ערכי קארי, מתוך אנציקלופדיית המקצוענות.
- **`data/boss_samples.md`**: מדביקים כאן 3 עד 5 תמלולים אמיתיים של המנהל, למשל מסרטונים קודמים. זה מה שהכי משפיע על האותנטיות.

## שימוש שוטף

```bash
# 1. מוסיפים נושאים ל-data/topics.csv (עמודות: topic, platform, versions)
python -m cari_video write

# או נושא בודד:
python -m cari_video add "למה לא לקנות רכב בלי בדיקת בוחן" --platform טיקטוק --versions 2

# 2. פותחים את data/scripts.csv באקסל, עורכים, ומשנים status ל-approved בתסריטים שאושרו

# 3. הפקה
python -m cari_video render            # מפיק, מחכה ומוריד ל-output/
python -m cari_video render --id 3 5   # רק תסריטים מסוימים
python -m cari_video render --no-wait  # רק שולח. הרצה חוזרת אוספת את מה שמוכן

python -m cari_video status
```

הגדרות וידאו בקובץ `.env`: `VIDEO_ORIENTATION` (`vertical` לרילס, טיקטוק וסטטוס, `horizontal` ליוטיוב ולאתר), `VIDEO_BACKGROUND` ו-`VIDEO_CAPTIONS`.

## כללי שימוש אחראי
- יש הסכמה כתובה של המנהל שמגדירה מה האווטאר רשאי להגיד ואיפה הסרטונים יפורסמו. המנהל יכול לבטל אותה בכל רגע.
- כל תסריט עובר אישור אנושי, ורצוי שגם המנהל יעבור על תסריטים רגישים.
- מציינים בפוסט שהסרטון נוצר בעזרת AI.
- בלי מחירים, מבצעים או הבטחות שלא נבדקו. ה-prompt כבר מורה ל-Claude לא להמציא כאלה.
- מפתחות ה-API נשמרים רק בקובץ `.env`, שלא עולה ל-git.

## בדיקות
```bash
python -m pytest -q
```
