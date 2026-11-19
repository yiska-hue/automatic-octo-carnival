"""חיבור ל-API של HeyGen: הפקת סרטון מאווטאר, בדיקת סטטוס והורדה.

תיעוד: https://docs.heygen.com/reference
"""
import time
from pathlib import Path

import requests

API = "https://api.heygen.com"
DIMENSIONS = {"vertical": (1080, 1920), "horizontal": (1920, 1080), "square": (1080, 1080)}


class HeyGenError(RuntimeError):
    pass


class HeyGen:
    def __init__(self, api_key: str, session: requests.Session | None = None):
        if not api_key:
            raise HeyGenError("חסר HEYGEN_API_KEY בקובץ .env")
        self.http = session or requests.Session()
        self.http.headers.update({"X-Api-Key": api_key, "Accept": "application/json"})

    def _get(self, path: str, **params) -> dict:
        r = self.http.get(API + path, params=params, timeout=60)
        return self._check(r)

    def _post(self, path: str, body: dict) -> dict:
        r = self.http.post(API + path, json=body, timeout=60)
        return self._check(r)

    @staticmethod
    def _check(r: requests.Response) -> dict:
        try:
            payload = r.json()
        except ValueError:
            raise HeyGenError(f"HTTP {r.status_code}: {r.text[:300]}")
        if r.status_code >= 400 or payload.get("error"):
            raise HeyGenError(f"HTTP {r.status_code}: {payload.get('error') or payload}")
        return payload.get("data") or {}

    def list_avatars(self) -> list[dict]:
        return self._get("/v2/avatars").get("avatars", [])

    def list_voices(self) -> list[dict]:
        return self._get("/v2/voices").get("voices", [])

    def create_video(self, *, text: str, avatar_id: str, voice_id: str, title: str = "",
                     orientation: str = "vertical", background: str = "#FFFFFF", captions: bool = True) -> str:
        width, height = DIMENSIONS.get(orientation, DIMENSIONS["vertical"])
        body = {
            "title": title,
            "caption": captions,
            "dimension": {"width": width, "height": height},
            "video_inputs": [{
                "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                "voice": {"type": "text", "input_text": text, "voice_id": voice_id},
                "background": {"type": "color", "value": background},
            }],
        }
        video_id = self._post("/v2/video/generate", body).get("video_id")
        if not video_id:
            raise HeyGenError("HeyGen לא החזיר video_id")
        return video_id

    def status(self, video_id: str) -> dict:
        return self._get("/v1/video_status.get", video_id=video_id)

    def wait(self, video_id: str, poll_seconds: int = 20, timeout_seconds: int = 1800) -> str:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            data = self.status(video_id)
            state = data.get("status")
            if state == "completed":
                return data["video_url"]
            if state == "failed":
                raise HeyGenError(f"ההפקה נכשלה: {data.get('error')}")
            time.sleep(poll_seconds)
        raise HeyGenError(f"תם הזמן בהמתנה לסרטון {video_id}")

    def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.http.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        return dest
