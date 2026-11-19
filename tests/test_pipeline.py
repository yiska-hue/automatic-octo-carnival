"""Offline tests: HeyGen and Claude are mocked."""
import dataclasses
from types import SimpleNamespace
from unittest import mock

import pytest

from cari_video import cli, heygen, scriptwriter, store


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    s = dataclasses.replace(
        cli.settings, heygen_api_key="k", avatar_id="av1", voice_id="vo1",
        scripts_csv=tmp_path / "scripts.csv", topics_csv=tmp_path / "topics.csv",
        output_dir=tmp_path / "output",
    )
    monkeypatch.setattr(cli, "settings", s)
    return s


class FakeResp:
    def __init__(self, data, status=200):
        self.status_code, self._data = status, data
        self.text = str(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        pass

    def iter_content(self, n):
        yield b"mp4bytes"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def test_store_roundtrip_hebrew(tmp_path):
    p = tmp_path / "s.csv"
    store.save(p, [{"id": "1", "title": "שלום", "script": "שורה, עם פסיק\nושורה שנייה", "status": "draft"}])
    rows = store.load(p)
    assert rows[0]["script"] == "שורה, עם פסיק\nושורה שנייה"
    assert store.next_id(rows) == 2


def test_write_creates_drafts(tmp_settings, monkeypatch):
    tmp_settings.topics_csv.write_text("topic,platform,versions\nנושא א,רילס,2\n", encoding="utf-8")
    fake = [scriptwriter.Script(title="t1", script="s1"), scriptwriter.Script(title="t2", script="s2")]
    monkeypatch.setattr(scriptwriter, "write_scripts", lambda *a, **k: fake)
    cli.main(["write"])
    rows = store.load(tmp_settings.scripts_csv)
    assert [r["status"] for r in rows] == ["draft", "draft"]
    cli.main(["write"])  # same topic is not rewritten
    assert len(store.load(tmp_settings.scripts_csv)) == 2


def test_render_only_approved(tmp_settings, monkeypatch):
    store.save(tmp_settings.scripts_csv, [
        {"id": "1", "title": "טיוטה", "script": "x", "status": "draft"},
        {"id": "2", "title": "מאושר", "script": "שלום לכולם", "status": "approved"},
    ])
    posted = []

    def fake_post(url, json, timeout):
        posted.append(json)
        return FakeResp({"data": {"video_id": "vid42"}})

    def fake_get(url, params=None, timeout=None, stream=False):
        if "video_status" in url:
            return FakeResp({"data": {"status": "completed", "video_url": "https://x/v.mp4"}})
        return FakeResp({})

    monkeypatch.setattr(heygen.requests.Session, "post", lambda self, *a, **k: fake_post(*a, **k))
    monkeypatch.setattr(heygen.requests.Session, "get", lambda self, *a, **k: fake_get(*a, **k))
    cli.main(["render"])

    assert len(posted) == 1
    body = posted[0]
    assert body["video_inputs"][0]["voice"]["input_text"] == "שלום לכולם"
    assert body["video_inputs"][0]["character"]["avatar_id"] == "av1"
    assert body["dimension"] == {"width": 1080, "height": 1920}
    rows = {r["id"]: r for r in store.load(tmp_settings.scripts_csv)}
    assert rows["1"]["status"] == "draft"
    assert rows["2"]["status"] == "done"
    assert (tmp_settings.output_dir / "002_מאושר.mp4").read_bytes() == b"mp4bytes"


def test_render_failure_marked(tmp_settings, monkeypatch):
    store.save(tmp_settings.scripts_csv, [{"id": "1", "title": "a", "script": "x", "status": "approved"}])
    monkeypatch.setattr(heygen.requests.Session, "post",
                        lambda self, *a, **k: FakeResp({"error": {"message": "bad avatar"}}, 400))
    cli.main(["render"])
    row = store.load(tmp_settings.scripts_csv)[0]
    assert row["status"] == "failed" and "bad avatar" in row["notes"]


def test_scriptwriter_request_shape(monkeypatch):
    client = mock.Mock()
    client.messages.parse.return_value = SimpleNamespace(
        stop_reason="end_turn",
        parsed_output=scriptwriter.ScriptBatch(scripts=[scriptwriter.Script(title="a", script="b")]),
    )
    out = scriptwriter.write_scripts("נושא", "רילס", 1, client=client)
    assert out[0].script == "b"
    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["output_format"] is scriptwriter.ScriptBatch
    assert "קארי" in kwargs["system"][0]["text"]


def test_scriptwriter_refusal(monkeypatch):
    client = mock.Mock()
    client.messages.parse.return_value = SimpleNamespace(stop_reason="refusal", parsed_output=None)
    with pytest.raises(RuntimeError):
        scriptwriter.write_scripts("x", "", 1, client=client)
