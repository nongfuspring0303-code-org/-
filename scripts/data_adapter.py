#!/usr/bin/env python3
"""
Data Adapter - 模拟新闻与市场数据接入
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request

try:
    import yaml
except ImportError:
    yaml = None

try:
    from edt_module_base import CacheManager
except ImportError:
    logging.warning("CacheManager import failed; DataAdapter cache is disabled.")
    CacheManager = None


class DataAdapter:
    """数据接入适配器（真实新闻流优先 + 模拟兜底）"""

    def __init__(self, config_path: Optional[str] = None):
        self.cache = CacheManager() if CacheManager else None
        self.config_path = config_path
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if not yaml:
            return {}
        path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "configs" / "edt-modules-config.yaml"
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def _get_config(self, path: str, default: Any = None) -> Any:
        keys = path.split(".")
        value: Any = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value

    def _safe_fetch_json(self, url: str, timeout: int) -> Optional[Dict[str, Any]]:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EDT-AI/1.0 (contact: admin@example.com)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            logging.warning("market_data_fetch_failed url=%s reason=%s", url, exc)
            return None

    def _get_int_config(self, path: str, default: int) -> int:
        value = self._get_config(path, default)
        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    def fetch_news(self) -> Dict[str, Any]:
        try:
            from ai_event_intel import NewsIngestion
        except ImportError as exc:
            logging.warning("NewsIngestion import failed; fallback news will be used: %s", exc)
            NewsIngestion = None

        if NewsIngestion:
            # 构建完整配置文件路径
            config_path = self.config_path
            if not config_path:
                config_path = str(Path(__file__).resolve().parent.parent / "configs" / "edt-modules-config.yaml")
            # 使用当前配置文件的超时设置
            out = NewsIngestion(config_path).run({"max_items": 1})
            if out.data.get("items"):
                item = out.data["items"][0]
                return {
                    "headline": item.get("headline", ""),
                    "source": item.get("source_url", ""),
                    "source_url": item.get("source_url", ""),
                    "source_type": item.get("source_type", ""),
                    "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "raw_text": item.get("raw_text", ""),
                    "metadata": {
                        "keywords": [],
                        "region": "US",
                        "asset_class": ["equities", "bonds", "usd"],
                        "trace_id": item.get("trace_id"),
                    },
                }

        return {
            "headline": "Federal Reserve announces emergency rate cut of 50bps",
            "source": "https://www.federalreserve.gov/newsevents/2026/march/h1234567a.htm",
            "source_url": "https://www.federalreserve.gov/newsevents/2026/march/h1234567a.htm",
            "source_type": "fallback",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_text": "The Federal Reserve has announced an emergency rate cut...",
            "metadata": {
                "keywords": ["Fed", "emergency", "rate cut"],
                "region": "US",
                "asset_class": ["equities", "bonds", "usd"],
                "trace_id": "TRC-FALLBACK-0001",
                "is_test_data": True,  # 标记为测试数据
                "test_data_note": "当无法获取真实新闻时使用的fallback测试数据",
            }
        }

    def _fetch_vix(self) -> Optional[Dict[str, Any]]:
        timeout = self._get_int_config("data_adapter.market_data.timeout_seconds", 5)
        url = self._get_config(
            "data_adapter.market_data.vix_url",
            "https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5EVIX",
        )
        payload = self._safe_fetch_json(url, timeout)
        if not payload:
            return None

        quote = (((payload.get("quoteResponse") or {}).get("result") or [None])[0]) or {}
        level = quote.get("regularMarketPrice")
        if level is None:
            return None
        return {
            "level": level,
            "change_pct": quote.get("regularMarketChangePercent"),
        }

    def _fetch_spx(self) -> Optional[Dict[str, Any]]:
        timeout = self._get_int_config("data_adapter.market_data.timeout_seconds", 5)
        url = self._get_config(
            "data_adapter.market_data.spx_url",
            "https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5EGSPC",
        )
        payload = self._safe_fetch_json(url, timeout)
        if not payload:
            return None

        quote = (((payload.get("quoteResponse") or {}).get("result") or [None])[0]) or {}
        change_pct = quote.get("regularMarketChangePercent")
        if change_pct is None:
            return None
        return {"change_pct": change_pct}

    def fetch_market_data(self) -> Dict[str, Any]:
        vix = self._fetch_vix()
        spx = self._fetch_spx()

        if vix and spx:
            return {
                "vix_level": vix.get("level"),
                "vix_change_pct": vix.get("change_pct"),
                "spx_change_pct": spx.get("change_pct"),
                "etf_volatility": {"change_pct": None},
                "market_data_source": "realtime",
                "is_test_data": False,
            }

        # Strict unavailable mode: no synthetic market fallback in production path.
        return {
            "vix_level": None,
            "vix_change_pct": None,
            "spx_change_pct": None,
            "etf_volatility": {"change_pct": None},
            "market_data_source": "failed",
            "is_test_data": True,
        }

    def fetch_sector_data(self) -> List[Dict[str, Any]]:
        # 仅使用 TwelveData（用户要求）
        results: List[Dict[str, Any]] = []
        try:
            from gov_data_fetcher import SectorETFFetcher

            etf = SectorETFFetcher().get_all_sectors().get("sectors", [])
            if etf:
                results = [
                    {
                        "symbol": item.get("symbol", ""),
                        "sector": item.get("name_en", ""),
                        "industry": item.get("name", ""),
                        "price": item.get("price"),
                        "change_pct": item.get("change_pct"),
                        "date": item.get("date"),
                        "source": "twelvedata",
                    }
                    for item in etf
                ]
        except Exception:
            pass

        return results

    def fetch(self) -> Dict[str, Any]:
        key = "mock_event" 
        if self.cache:
            cached = self.cache.run({"action": "get", "key": key}).data
            if cached.get("hit"):
                return cached.get("value")

        payload = {
            "news": self.fetch_news(),
            "market_data": self.fetch_market_data(),
            "sector_data": self.fetch_sector_data(),
        }

        if self.cache:
            self.cache.run({"action": "set", "key": key, "value": payload, "ttl_seconds": 300})
        return payload


if __name__ == "__main__":
    adapter = DataAdapter()
    data = adapter.fetch()
    print("DataAdapter OK")
    print(data)
