"""
Pulse SDK — Real-time truth layer for AI agents.

One-line integration:
    from pulse import feed
    context = feed.get("gas_price")
    # returns: {value, confidence, sources, refreshed_at, latency_ms}
"""

import httpx
import json
import threading
import websocket
from typing import Optional, Callable, Dict, Any, Union
from dataclasses import dataclass


PULSE_URL = "http://localhost:7070"


@dataclass
class PulseFeed:
    feed_id: str
    query: str
    value: Any
    confidence: float
    source_count: int
    agreement_score: float
    latency_ms: int
    refreshed_at: str
    sources: list

    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8

    def summary(self) -> str:
        return (
            f"[Pulse] {self.query}\n"
            f"  value={self.value}\n"
            f"  confidence={self.confidence:.0%} | sources={self.source_count} | "
            f"agreement={self.agreement_score:.0%} | latency={self.latency_ms}ms"
        )


class PulseClient:
    """Synchronous Pulse client. Use feed.get() for one-shot queries."""

    def __init__(self, base_url: str = PULSE_URL, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def get(
        self,
        feed_type: str,
        query: Optional[str] = None,
        fresh: bool = False,
    ) -> PulseFeed:
        """
        Pull a verified data feed from Pulse.

        Args:
            feed_type: "gas_price" | "crypto_price" | "on_chain" | "news" | "sentiment"
            query: Optional search query, e.g. "ETH gas price" or "bitcoin"
            fresh: If True, bypass cache and fetch fresh data

        Returns:
            PulseFeed with value, confidence, sources, latency

        Example:
            context = feed.get("gas_price")
            if context.value["safe_gwei"] > 50:
                print("Gas is high — wait before transacting")
        """
        params: Dict[str, Any] = {}
        if query:
            params["q"] = query
        if fresh:
            params["fresh"] = "true"

        resp = self._client.get(
            f"{self.base_url}/feed/{feed_type}",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        return _parse_feed(data)

    def subscribe(
        self,
        feed_type: str,
        query: Optional[str] = None,
        on_update: Callable[[PulseFeed], None] = None,
    ) -> "PulseSubscription":
        """
        Subscribe to a live Pulse feed over WebSocket.
        Updates arrive every ~10 seconds.

        Example:
            def on_gas(ctx):
                print(f"Gas: {ctx.value['safe_gwei']} gwei ({ctx.confidence:.0%} confidence)")

            sub = feed.subscribe("gas_price", on_update=on_gas)
            sub.start()  # non-blocking
            # ...
            sub.stop()
        """
        params = f"?q={query}" if query else ""
        ws_url = f"{self.base_url.replace('http', 'ws')}/feed/{feed_type}/ws{params}"
        return PulseSubscription(ws_url, on_update)

    def health(self) -> bool:
        try:
            resp = self._client.get(f"{self.base_url}/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()


class PulseSubscription:
    """WebSocket subscription to a live Pulse feed."""

    def __init__(self, ws_url: str, on_update: Callable[[PulseFeed], None]):
        self.ws_url = ws_url
        self.on_update = on_update
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        def on_message(ws, message):
            if not self._running:
                ws.close()
                return
            try:
                data = json.loads(message)
                feed = _parse_feed(data)
                if self.on_update:
                    self.on_update(feed)
            except Exception as e:
                print(f"[pulse] parse error: {e}")

        def on_error(ws, error):
            print(f"[pulse] ws error: {error}")

        ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
        )
        ws.run_forever()


def _parse_feed(data: dict) -> PulseFeed:
    return PulseFeed(
        feed_id=data.get("feed_id", ""),
        query=data.get("query", ""),
        value=data.get("value"),
        confidence=data.get("confidence", 0.0),
        source_count=data.get("source_count", 0),
        agreement_score=data.get("agreement_score", 0.0),
        latency_ms=data.get("latency_ms", 0),
        refreshed_at=data.get("refreshed_at", ""),
        sources=data.get("sources", []),
    )


# Default singleton client
_default_client = PulseClient()

# Module-level convenience API
class _FeedNamespace:
    """
    Module-level feed API. Import and use directly:

        from pulse import feed
        ctx = feed.get("gas_price")
    """

    def get(self, feed_type: str, query: str = None, fresh: bool = False) -> PulseFeed:
        return _default_client.get(feed_type, query=query, fresh=fresh)

    def subscribe(self, feed_type: str, query: str = None, on_update=None) -> PulseSubscription:
        return _default_client.subscribe(feed_type, query=query, on_update=on_update)

    def health(self) -> bool:
        return _default_client.health()


feed = _FeedNamespace()

__all__ = ["feed", "PulseClient", "PulseFeed", "PulseSubscription"]
