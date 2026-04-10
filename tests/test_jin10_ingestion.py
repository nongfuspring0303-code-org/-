import os
import tempfile
import json
import yaml

from scripts.ai_event_intel import NewsIngestion


def test_jin10_fetch_returns_empty_when_no_token():
    cfg = {
        "modules": {
            "NewsIngestion": {
                "params": {
                    "enable_jin10": True,
                    "jin10": {
                        "mcp_url": "https://mcp.jin10.com/mcp",
                        "token_env": "JIN10_MCP_TOKEN_TEST",
                    },
                    "sources": [],
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
        path = f.name

    try:
        if "JIN10_MCP_TOKEN_TEST" in os.environ:
            os.environ.pop("JIN10_MCP_TOKEN_TEST")
        ingestion = NewsIngestion(path)
        items = ingestion._fetch_jin10(timeout=1)
        assert items == []
    finally:
        os.unlink(path)


def test_jin10_fetch_success_sse():
    cfg = {
        "modules": {
            "NewsIngestion": {
                "params": {
                    "enable_jin10": True,
                    "jin10": {
                        "mcp_url": "https://mcp.jin10.com/mcp",
                        "token_env": "JIN10_MCP_TOKEN_TEST",
                    },
                    "sources": [],
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
        path = f.name

    class DummyResp:
        def __init__(self, text: str):
            self._text = text
            self.headers = {"mcp-session-id": "abc"}
        def read(self):
            return self._text.encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=10):
        body = json.dumps({"jsonrpc": "2.0", "result": {"structuredContent": {"data": {"items": [
            {"content": "hello", "time": "2026-04-11T00:00:00Z", "url": "https://x"}
        ]}}}})
        sse = f"event: message\ndata: {body}\n\n"
        return DummyResp(sse)

    try:
        os.environ["JIN10_MCP_TOKEN_TEST"] = "Bearer test"
        import urllib.request
        _orig = urllib.request.urlopen
        urllib.request.urlopen = fake_urlopen  # type: ignore
        ingestion = NewsIngestion(path)
        items = ingestion._fetch_jin10(timeout=1)
        assert items and items[0]["source_type"] == "jin10"
    finally:
        try:
            urllib.request.urlopen = _orig  # type: ignore
        except Exception:
            pass
        os.environ.pop("JIN10_MCP_TOKEN_TEST", None)
        os.unlink(path)


def test_jin10_fetch_degrades_on_bad_json():
    cfg = {
        "modules": {
            "NewsIngestion": {
                "params": {
                    "enable_jin10": True,
                    "jin10": {
                        "mcp_url": "https://mcp.jin10.com/mcp",
                        "token_env": "JIN10_MCP_TOKEN_TEST",
                    },
                    "sources": [],
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
        path = f.name

    class DummyResp:
        def __init__(self, text: str):
            self._text = text
            self.headers = {"mcp-session-id": "abc"}
        def read(self):
            return self._text.encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=10):
        sse = "event: message\ndata: {bad_json}\n\n"
        return DummyResp(sse)

    try:
        os.environ["JIN10_MCP_TOKEN_TEST"] = "Bearer test"
        import urllib.request
        _orig = urllib.request.urlopen
        urllib.request.urlopen = fake_urlopen  # type: ignore
        ingestion = NewsIngestion(path)
        items = ingestion._fetch_jin10(timeout=1)
        assert items == []
    finally:
        try:
            urllib.request.urlopen = _orig  # type: ignore
        except Exception:
            pass
        os.environ.pop("JIN10_MCP_TOKEN_TEST", None)
        os.unlink(path)
