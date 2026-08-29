#!/usr/bin/env python3
"""
Pulse Auth + Data Service — port 7072
Auth: signup, login, Google OAuth, API keys, category prefs.
Data: 20 categories, 80+ free sources, no-key Phase 1 fully wired.
"""

import asyncio, hashlib, os, secrets, time, uuid, xml.etree.ElementTree as ET
import re, html
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
import aiosqlite
import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY   = os.getenv("JWT_SECRET", secrets.token_hex(32))
ALGORITHM    = "HS256"
TOKEN_EXPIRE = 60 * 24 * 7
DB_PATH      = os.getenv("DB_PATH", "/root/pulse/pulse.db")
PULSE_API    = os.getenv("PULSE_API_URL", "http://localhost:7070")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:7071/auth/google/callback")

# Phase 2 keys (optional — feeds degrade gracefully without them)
FINNHUB_KEY       = os.getenv("FINNHUB_KEY", "")
NEWSDATA_KEY      = os.getenv("NEWSDATA_KEY", "")
GNEWS_KEY         = os.getenv("GNEWS_KEY", "")
CMC_KEY           = os.getenv("CMC_KEY", "")
ETHERSCAN_KEY     = os.getenv("ETHERSCAN_KEY", "")
NASA_KEY          = os.getenv("NASA_KEY", "DEMO_KEY")
OPENAQ_KEY        = os.getenv("OPENAQ_KEY", "")
FRED_KEY          = os.getenv("FRED_KEY", "")

# ── Categories ─────────────────────────────────────────────────────────────────
CATEGORIES = {
    "crypto":        {"label": "Crypto & Web3",          "icon": "₿",  "desc": "BTC, ETH, SOL prices — Binance, CoinGecko, CoinCap, Fear & Greed"},
    "onchain":       {"label": "On-Chain & Network",      "icon": "⛓",  "desc": "BTC mempool, fees, block height, ETH gas, network stats"},
    "defi":          {"label": "DeFi & Stablecoins",      "icon": "🏦",  "desc": "DeFiLlama TVL, protocol fees, stablecoin market caps"},
    "finance":       {"label": "Finance & Markets",       "icon": "📈",  "desc": "FX rates, stock indices, gold, oil, treasury yields"},
    "economics":     {"label": "Macro Economics",         "icon": "🌐",  "desc": "GDP, inflation, unemployment — World Bank, FRED, BLS"},
    "news":          {"label": "Breaking News",           "icon": "📰",  "desc": "HackerNews, Reddit worldnews, Dev.to top stories"},
    "weather":       {"label": "Weather & Alerts",        "icon": "🌤",  "desc": "Open-Meteo global, wttr.in, NOAA active alerts"},
    "climate":       {"label": "Climate & Environment",   "icon": "🌍",  "desc": "CO2, methane, sea level, ice — NOAA + NASA via ClimateMonitor"},
    "air":           {"label": "Air Quality",             "icon": "💨",  "desc": "PM2.5, ozone, NO2 — OpenAQ + Open-Meteo air quality"},
    "disasters":     {"label": "Natural Disasters",       "icon": "⚠️",  "desc": "USGS earthquakes, NOAA hurricane/tornado/flood warnings"},
    "space":         {"label": "Space & Astronomy",       "icon": "🔭",  "desc": "ISS location, astronauts in space, SpaceX, upcoming launches, NASA APOD"},
    "science":       {"label": "Science & Research",      "icon": "🧬",  "desc": "arXiv AI papers, PubMed medical research, clinical trials"},
    "medical":       {"label": "Health & Medical",        "icon": "🩺",  "desc": "FDA drug/food/device recalls, WHO outbreaks, ClinicalTrials"},
    "tech":          {"label": "Tech & Dev",              "icon": "⚙️",  "desc": "HackerNews best, npm/PyPI stats, Dev.to, GitHub activity"},
    "cybersecurity": {"label": "Cybersecurity",           "icon": "🔒",  "desc": "NVD CVEs published today, active threat intel"},
    "sports":        {"label": "Sports",                  "icon": "⚽",  "desc": "Live scores, fixtures — TheSportsDB, ESPN"},
    "gaming":        {"label": "Gaming",                  "icon": "🎮",  "desc": "Steam live player counts for top games"},
    "social":        {"label": "Social & Trends",         "icon": "📡",  "desc": "Reddit trending, Wikipedia top articles, Bluesky"},
    "politics":      {"label": "Politics & Policy",       "icon": "🏛",  "desc": "US legislation, GDELT global events, government feeds"},
    "aviation":      {"label": "Aviation & Transport",    "icon": "✈️",  "desc": "Live aircraft via OpenSky Network, flight density"},
    "jobs":          {"label": "Jobs & Labor",            "icon": "💼",  "desc": "Remote jobs (Remotive), US unemployment rate (BLS)"},
    "commodities":   {"label": "Commodities",             "icon": "🏭",  "desc": "Gold, silver, oil, gas — free exchange data"},
}

# ── DB ────────────────────────────────────────────────────────────────────────
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT,
            password    TEXT,
            google_id   TEXT,
            created_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash    TEXT PRIMARY KEY,
            key_prefix  TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            label       TEXT DEFAULT 'Default',
            created_at  TEXT NOT NULL,
            last_used   TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS user_categories (
            user_id     TEXT NOT NULL,
            category    TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_keys_user ON api_keys(user_id);
        """)
        await db.commit()

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def make_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

async def get_current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get("pulse_token") or (
        request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None
    )
    if not token:
        raise HTTPException(401, "Not authenticated")
    uid = decode_token(token)
    if not uid:
        raise HTTPException(401, "Invalid or expired token")
    async with db.execute("SELECT * FROM users WHERE id=?", (uid,)) as cur:
        user = await cur.fetchone()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Pulse Auth + Data", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ── Schemas ───────────────────────────────────────────────────────────────────
class SignupBody(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginBody(BaseModel):
    email: str
    password: str

class CategoryUpdate(BaseModel):
    categories: list[str]

# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/signup")
async def signup(body: SignupBody, db=Depends(get_db)):
    async with db.execute("SELECT id FROM users WHERE email=?", (body.email.lower(),)) as cur:
        if await cur.fetchone():
            raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    hashed = _bcrypt.hashpw(body.password.encode(), _bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO users (id,email,name,password,created_at) VALUES (?,?,?,?,?)",
        (uid, body.email.lower(), body.name or body.email.split("@")[0], hashed, now)
    )
    for cat in CATEGORIES:
        await db.execute(
            "INSERT OR IGNORE INTO user_categories (user_id,category,enabled) VALUES (?,?,1)",
            (uid, cat)
        )
    await db.commit()
    token = make_token(uid)
    resp = JSONResponse({"ok": True, "user_id": uid})
    resp.set_cookie("pulse_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return resp

@app.post("/auth/login")
async def login(body: LoginBody, db=Depends(get_db)):
    async with db.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)) as cur:
        user = await cur.fetchone()
    if not user or not user["password"] or not _bcrypt.checkpw(body.password.encode(), user["password"].encode()):
        raise HTTPException(401, "Invalid email or password")
    token = make_token(user["id"])
    resp = JSONResponse({"ok": True, "name": user["name"]})
    resp.set_cookie("pulse_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return resp

@app.post("/auth/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("pulse_token")
    return resp

@app.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "name": user["name"]}

@app.get("/auth/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    params = (
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")

@app.get("/auth/google/callback")
async def google_callback(code: str, db=Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    async with httpx.AsyncClient() as c:
        token_r = await c.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI, "grant_type": "authorization_code"
        })
        tokens = token_r.json()
        id_token = tokens.get("id_token", "")
        info_r = await c.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        info = info_r.json()

    email = info.get("email", "").lower()
    gid   = info.get("sub", "")
    name  = info.get("name", email.split("@")[0])
    if not email:
        raise HTTPException(400, "Could not retrieve email from Google")

    async with db.execute("SELECT * FROM users WHERE email=?", (email,)) as cur:
        user = await cur.fetchone()

    if user:
        uid = user["id"]
    else:
        uid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO users (id,email,name,google_id,created_at) VALUES (?,?,?,?,?)",
            (uid, email, name, gid, now)
        )
        for cat in CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO user_categories (user_id,category,enabled) VALUES (?,?,1)",
                (uid, cat)
            )
        await db.commit()

    token = make_token(uid)
    resp = RedirectResponse("/dashboard")
    resp.set_cookie("pulse_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return resp

# ══════════════════════════════════════════════════════════════════════════════
# API KEY ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/keys/generate")
async def generate_key(label: str = "Default", user=Depends(get_current_user), db=Depends(get_db)):
    raw_key = "pk_" + secrets.token_urlsafe(32)
    prefix  = raw_key[:12]
    kh      = hash_key(raw_key)
    now     = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO api_keys (key_hash,key_prefix,user_id,label,created_at) VALUES (?,?,?,?,?)",
        (kh, prefix, user["id"], label, now)
    )
    await db.commit()
    return {"key": raw_key, "prefix": prefix, "label": label,
            "note": "Store this key — it will not be shown again."}

@app.get("/auth/keys")
async def list_keys(user=Depends(get_current_user), db=Depends(get_db)):
    async with db.execute(
        "SELECT key_prefix,label,created_at,last_used FROM api_keys WHERE user_id=? ORDER BY created_at DESC",
        (user["id"],)
    ) as cur:
        keys = [dict(r) for r in await cur.fetchall()]
    return {"keys": keys}

@app.delete("/auth/keys/{prefix}")
async def delete_key(prefix: str, user=Depends(get_current_user), db=Depends(get_db)):
    await db.execute(
        "DELETE FROM api_keys WHERE key_prefix=? AND user_id=?", (prefix, user["id"])
    )
    await db.commit()
    return {"ok": True}

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/auth/categories")
async def get_categories(user=Depends(get_current_user), db=Depends(get_db)):
    async with db.execute(
        "SELECT category,enabled FROM user_categories WHERE user_id=?", (user["id"],)
    ) as cur:
        rows = {r["category"]: bool(r["enabled"]) for r in await cur.fetchall()}
    result = {}
    for key, meta in CATEGORIES.items():
        result[key] = {**meta, "enabled": rows.get(key, True)}
    return result

@app.post("/auth/categories")
async def update_categories(body: CategoryUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    enabled_set = set(body.categories)
    for cat in CATEGORIES:
        enabled = 1 if cat in enabled_set else 0
        await db.execute(
            "INSERT INTO user_categories (user_id,category,enabled) VALUES (?,?,?) "
            "ON CONFLICT(user_id,category) DO UPDATE SET enabled=excluded.enabled",
            (user["id"], cat, enabled)
        )
    await db.commit()
    return {"ok": True, "enabled": list(enabled_set)}

# ══════════════════════════════════════════════════════════════════════════════
# LIVE DATA FEEDS — 22 categories, 80+ sources
# ══════════════════════════════════════════════════════════════════════════════

_cache: dict = {}

async def _cached(feed_id: str, ttl: int, fetch_fn):
    entry = _cache.get(feed_id)
    if entry and time.time() - entry["fetched_at"] < ttl:
        return entry["data"]
    try:
        data = await fetch_fn()
        _cache[feed_id] = {"data": data, "fetched_at": time.time()}
        return data
    except Exception as e:
        if entry:
            return entry["data"]
        return {"error": str(e)}

async def _get(url, headers=None, timeout=10):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                  headers={"User-Agent": "pulse-agent/1.0", **(headers or {})}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()

async def _get_text(url, headers=None, timeout=10):
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                  headers={"User-Agent": "pulse-agent/1.0", **(headers or {})}) as c:
        r = await c.get(url)
        return r.text

async def _gather(*coros):
    return await asyncio.gather(*coros, return_exceptions=True)

def _ok(result):
    return result if not isinstance(result, Exception) else None

# ─────────────────────────────────────────────────────────────────────────────
# RSS ENGINE — pull, parse, normalize any RSS/Atom feed, no key ever
# ─────────────────────────────────────────────────────────────────────────────
def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()[:300]

async def _fetch_rss(url: str, limit: int = 8) -> list[dict]:
    """Fetch and parse an RSS or Atom feed. Returns list of {title, url, published, summary, source}."""
    try:
        text = await _get_text(url, timeout=10)
        root = ET.fromstring(text)
        ns   = {
            "atom":    "http://www.w3.org/2005/Atom",
            "media":   "http://search.yahoo.com/mrss/",
            "content": "http://purl.org/rss/1.0/modules/content/",
            "dc":      "http://purl.org/dc/elements/1.1/",
        }
        items = []

        # Atom feed
        if root.tag.endswith("feed"):
            for entry in root.findall("atom:entry", ns)[:limit]:
                link = next((l.get("href","") for l in entry.findall("atom:link", ns)
                             if l.get("rel","alternate") in ("alternate","")), "")
                items.append({
                    "title":     _strip_tags(entry.findtext("atom:title", "", ns)),
                    "url":       link,
                    "published": _strip_tags(entry.findtext("atom:updated", "", ns) or entry.findtext("atom:published", "", ns)),
                    "summary":   _strip_tags(entry.findtext("atom:summary", "", ns))[:200],
                })
        else:
            # RSS 2.0
            channel = root.find("channel")
            feed_source = (channel.findtext("title") if channel is not None else "") or ""
            for item in (channel or root).findall("item")[:limit]:
                pub = (item.findtext("pubDate") or item.findtext("dc:date", "", ns) or "")[:40]
                desc = item.findtext("description") or item.findtext("content:encoded", "", ns) or ""
                items.append({
                    "title":     _strip_tags(item.findtext("title") or ""),
                    "url":       (item.findtext("link") or item.findtext("guid") or ""),
                    "published": pub,
                    "summary":   _strip_tags(desc)[:200],
                    "source":    feed_source,
                })

        return [i for i in items if i.get("title")]
    except Exception:
        return []

async def _multi_rss(feeds: list[tuple[str, str]], limit_per_feed: int = 5, total: int = 30) -> list[dict]:
    """Fetch multiple RSS feeds concurrently. feeds = [(label, url), ...]"""
    tasks = [_fetch_rss(url, limit_per_feed) for _, url in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for (label, _), res in zip(feeds, results):
        if not isinstance(res, Exception):
            for item in res:
                item["feed"] = label
                out.append(item)
    # deduplicate by title
    seen = set()
    deduped = []
    for item in out:
        key = item["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:total]

# ─────────────────────────────────────────────────────────────────────────────
# 1. CRYPTO — Binance + CoinGecko + CoinCap + Fear&Greed + Kraken
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_crypto():
    coins = ["bitcoin", "ethereum", "solana", "avalanche-2", "polkadot", "cardano", "dogecoin", "shiba-inu"]
    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOTUSDT", "ADAUSDT", "DOGEUSDT"]

    gecko_task   = _get(f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(coins)}&vs_currencies=usd&include_24hr_change=true")
    binance_task = _get("https://api.binance.com/api/v3/ticker/24hr")
    fear_task    = _get("https://api.alternative.me/fng/")
    coincap_task = _get("https://api.coincap.io/v2/assets?limit=10")

    gecko_r, binance_r, fear_r, coincap_r = await _gather(gecko_task, binance_task, fear_task, coincap_task)

    prices = {}

    # CoinGecko
    if _ok(gecko_r):
        for coin, vals in gecko_r.items():
            prices[coin] = {
                "price_usd": vals.get("usd"),
                "change_24h": round(vals.get("usd_24h_change", 0) or 0, 2),
                "source": "coingecko",
            }

    # Binance (override/enrich)
    if _ok(binance_r) and isinstance(binance_r, list):
        binance_map = {t["symbol"]: t for t in binance_r if t["symbol"] in pairs}
        symbol_to_coin = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
            "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot", "ADAUSDT": "cardano",
            "DOGEUSDT": "dogecoin",
        }
        for sym, coin in symbol_to_coin.items():
            if sym in binance_map:
                t = binance_map[sym]
                prices[coin] = {
                    "price_usd": float(t["lastPrice"]),
                    "change_24h": round(float(t["priceChangePercent"]), 2),
                    "high_24h": float(t["highPrice"]),
                    "low_24h": float(t["lowPrice"]),
                    "volume_24h": float(t["volume"]),
                    "source": "binance",
                }

    # Fear & Greed
    fear = None
    if _ok(fear_r):
        d = fear_r.get("data", [{}])[0]
        fear = {"value": int(d.get("value", 0)), "label": d.get("value_classification", ""), "source": "alternative.me"}

    # CoinCap top 10
    cap_top = []
    if _ok(coincap_r):
        for a in (coincap_r.get("data") or [])[:10]:
            cap_top.append({
                "name": a.get("name"), "symbol": a.get("symbol"),
                "price_usd": round(float(a.get("priceUsd") or 0), 4),
                "change_24h": round(float(a.get("changePercent24Hr") or 0), 2),
                "market_cap_usd": int(float(a.get("marketCapUsd") or 0)),
            })

    return {"prices": prices, "fear_greed": fear, "top10_by_mcap": cap_top}

# ─────────────────────────────────────────────────────────────────────────────
# 2. ON-CHAIN — Mempool.space + Blockchain.info + Blockchair + Etherscan
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_onchain():
    fees_t    = _get("https://mempool.space/api/v1/fees/recommended")
    mempool_t = _get("https://mempool.space/api/mempool")
    height_t  = _get_text("https://mempool.space/api/blocks/tip/height")
    btc_t     = _get("https://blockchain.info/stats?format=json")
    chair_t   = _get("https://api.blockchair.com/bitcoin/stats")

    fees_r, mempool_r, height_r, btc_r, chair_r = await _gather(fees_t, mempool_t, height_t, btc_t, chair_t)

    btc_network = {}
    if _ok(btc_r):
        btc_network = {
            "hash_rate_ths": round((btc_r.get("hash_rate") or 0) / 1e12, 2),
            "difficulty": btc_r.get("difficulty"),
            "blocks_mined_today": btc_r.get("n_blocks_mined"),
            "btc_sent_today": btc_r.get("estimated_btc_sent"),
            "tx_count_today": btc_r.get("n_tx"),
        }

    chair_data = {}
    if _ok(chair_r) and chair_r.get("data"):
        d = chair_r["data"]
        chair_data = {
            "circulating_supply": d.get("circulation"),
            "market_price_usd": d.get("market_price_usd"),
            "transactions_24h": d.get("transactions_24h"),
        }

    result = {
        "bitcoin": {
            "block_height": int(height_r.strip()) if _ok(height_r) and height_r else None,
            "mempool_count": _ok(mempool_r) and mempool_r.get("count"),
            "mempool_vsize_mb": round((_ok(mempool_r) and mempool_r.get("vsize") or 0) / 1e6, 2),
            "fee_fastest_sat_vb": _ok(fees_r) and fees_r.get("fastestFee"),
            "fee_30min_sat_vb":   _ok(fees_r) and fees_r.get("halfHourFee"),
            "fee_1h_sat_vb":      _ok(fees_r) and fees_r.get("hourFee"),
            "fee_economy_sat_vb": _ok(fees_r) and fees_r.get("economyFee"),
            **btc_network,
            **chair_data,
        }
    }

    # ETH gas via Etherscan if key present
    if ETHERSCAN_KEY:
        try:
            gas = await _get(f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={ETHERSCAN_KEY}")
            r = gas.get("result", {})
            result["ethereum"] = {
                "gas_safe_gwei": r.get("SafeGasPrice"),
                "gas_proposed_gwei": r.get("ProposeGasPrice"),
                "gas_fast_gwei": r.get("FastGasPrice"),
                "base_fee_gwei": r.get("suggestBaseFee"),
            }
        except Exception:
            pass

    return result

# ─────────────────────────────────────────────────────────────────────────────
# 3. DEFI — DeFiLlama TVL + chains + stablecoins + fees
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_defi():
    protocols_t   = _get("https://api.llama.fi/v2/protocols")
    chains_t      = _get("https://api.llama.fi/v2/chains")
    stables_t     = _get("https://stablecoins.llama.fi/stablecoins?includePrices=true")

    protocols_r, chains_r, stables_r = await _gather(protocols_t, chains_t, stables_t)

    top_protocols = []
    if _ok(protocols_r) and isinstance(protocols_r, list):
        for p in sorted(protocols_r, key=lambda x: x.get("tvl") or 0, reverse=True)[:15]:
            top_protocols.append({
                "name": p.get("name"),
                "chain": p.get("chain"),
                "tvl_usd": int(p.get("tvl") or 0),
                "change_1d": round(p.get("change_1d") or 0, 2),
                "change_7d": round(p.get("change_7d") or 0, 2),
                "category": p.get("category"),
            })

    top_chains = []
    if _ok(chains_r) and isinstance(chains_r, list):
        for c in sorted(chains_r, key=lambda x: x.get("tvl") or 0, reverse=True)[:10]:
            top_chains.append({
                "name": c.get("name"),
                "tvl_usd": int(c.get("tvl") or 0),
            })

    top_stables = []
    if _ok(stables_r):
        for s in (stables_r.get("peggedAssets") or [])[:10]:
            circ = s.get("circulating", {})
            top_stables.append({
                "name": s.get("name"),
                "symbol": s.get("symbol"),
                "peg_type": s.get("pegType"),
                "circulating_usd": int(circ.get("peggedUSD") or 0),
            })

    total_tvl = sum(p["tvl_usd"] for p in top_protocols)
    return {
        "total_defi_tvl_usd": total_tvl,
        "top_protocols": top_protocols,
        "top_chains_by_tvl": top_chains,
        "top_stablecoins": top_stables,
        "source": "DeFiLlama",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. FINANCE — FX + Yahoo indices + Frankfurter ECB
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_finance():
    fx_t   = _get("https://api.exchangerate-api.com/v4/latest/USD")
    ecb_t  = _get("https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,JPY,CHF,CNY")

    indices_syms = ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^N225", "^HSI"]
    idx_tasks = [
        _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range=1d")
        for s in indices_syms
    ]

    results = await _gather(fx_t, ecb_t, *idx_tasks)
    fx_r, ecb_r = results[0], results[1]
    idx_results = results[2:]

    # FX rates
    fx = {}
    if _ok(fx_r):
        keep = ["EUR","GBP","JPY","CAD","AUD","CHF","CNY","INR","BRL","KRW","MXN","SGD","NOK","SEK","TRY"]
        rates = fx_r.get("rates", {})
        fx = {k: rates[k] for k in keep if k in rates}

    # ECB cross-rates
    ecb = {}
    if _ok(ecb_r):
        ecb = ecb_r.get("rates", {})

    # Stock indices
    indices = {}
    labels  = {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "Dow Jones",
                "^FTSE": "FTSE 100", "^N225": "Nikkei 225", "^HSI": "Hang Seng"}
    for sym, res in zip(indices_syms, idx_results):
        if _ok(res):
            try:
                meta   = res["chart"]["result"][0]["meta"]
                price  = meta.get("regularMarketPrice")
                prev   = meta.get("previousClose") or meta.get("chartPreviousClose")
                change = round(((price - prev) / prev) * 100, 2) if price and prev else None
                indices[labels[sym]] = {"price": price, "change_pct": change, "currency": meta.get("currency")}
            except Exception:
                pass

    return {"base": "USD", "fx_rates": fx, "ecb_eur_rates": ecb, "indices": indices}

# ─────────────────────────────────────────────────────────────────────────────
# 5. ECONOMICS — World Bank + BLS + FRED (if key)
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_economics():
    # World Bank GDP growth
    wb_t = _get(
        "https://api.worldbank.org/v2/country/US;CN;GB;JP;DE;IN;BR;FR"
        "/indicator/NY.GDP.MKTP.KD.ZG?format=json&mrv=1&per_page=20"
    )
    # World Bank inflation
    cpi_t = _get(
        "https://api.worldbank.org/v2/country/US;CN;GB;JP;DE/indicator/FP.CPI.TOTL.ZG"
        "?format=json&mrv=1&per_page=10"
    )
    # BLS unemployment
    bls_t = _get("https://api.bls.gov/publicAPI/v1/timeseries/data/LNS14000000")

    wb_r, cpi_r, bls_r = await _gather(wb_t, cpi_t, bls_t)

    gdp = {}
    if _ok(wb_r) and isinstance(wb_r, list) and len(wb_r) > 1:
        for r in (wb_r[1] or []):
            if r and r.get("value") is not None:
                gdp[r["country"]["id"]] = {
                    "country": r["country"]["value"],
                    "gdp_growth_pct": round(r["value"], 2),
                    "year": r["date"],
                }

    inflation = {}
    if _ok(cpi_r) and isinstance(cpi_r, list) and len(cpi_r) > 1:
        for r in (cpi_r[1] or []):
            if r and r.get("value") is not None:
                inflation[r["country"]["id"]] = {
                    "country": r["country"]["value"],
                    "inflation_pct": round(r["value"], 2),
                    "year": r["date"],
                }

    unemployment = None
    if _ok(bls_r):
        try:
            latest = bls_r["Results"]["series"][0]["data"][0]
            unemployment = {
                "rate_pct": float(latest["value"]),
                "period": f"{latest['periodName']} {latest['year']}",
                "source": "BLS",
            }
        except Exception:
            pass

    result = {
        "gdp_growth": gdp,
        "inflation": inflation,
        "us_unemployment": unemployment,
        "source": "World Bank + BLS",
    }

    if FRED_KEY:
        try:
            fed = await _get(
                f"https://api.stlouisfed.org/fred/series/observations?series_id=DFF"
                f"&api_key={FRED_KEY}&file_type=json&limit=1&sort_order=desc"
            )
            obs = fed.get("observations", [{}])[0]
            result["fed_funds_rate"] = {"rate_pct": float(obs.get("value", 0)), "date": obs.get("date"), "source": "FRED"}
        except Exception:
            pass

    return result

# ─────────────────────────────────────────────────────────────────────────────
# 6. NEWS — 20+ RSS sources: Reuters, AP, BBC, Al Jazeera, Guardian, NPR, etc.
# ─────────────────────────────────────────────────────────────────────────────
NEWS_FEEDS = [
    ("Reuters World",      "https://feeds.reuters.com/reuters/worldNews"),
    ("AP Top News",        "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World",          "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera",         "https://www.aljazeera.com/xml/rss/all.xml"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
    ("NPR News",           "https://feeds.npr.org/1001/rss.xml"),
    ("Axios",              "https://api.axios.com/feed/"),
    ("Politico",           "https://rss.politico.com/politics-news.xml"),
    ("The Hill",           "https://thehill.com/feed/"),
    ("Euronews",           "https://feeds.feedburner.com/euronews/en/news/"),
    ("Deutsche Welle",     "https://rss.dw.com/xml/rss-en-all"),
    ("France 24",          "https://www.france24.com/en/rss"),
    ("South China Morning Post", "https://www.scmp.com/rss/91/feed"),
    ("Times of India",     "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"),
    ("HackerNews Top",     "https://news.ycombinator.com/rss"),
    ("Reddit WorldNews",   "https://www.reddit.com/r/worldnews/.rss"),
]

async def fetch_news():
    articles = await _multi_rss(NEWS_FEEDS, limit_per_feed=4, total=40)
    return {"articles": articles, "source_count": len(NEWS_FEEDS), "sources": [f for f, _ in NEWS_FEEDS]}

# ─────────────────────────────────────────────────────────────────────────────
# 7. WEATHER — Open-Meteo + wttr.in + NOAA alerts
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_weather():
    metro_coords = [
        ("New York",    40.71, -74.01),
        ("London",      51.51, -0.13),
        ("Tokyo",       35.68, 139.69),
        ("Dubai",       25.20, 55.27),
        ("São Paulo",   -23.55, -46.63),
        ("Lagos",       6.45, 3.39),
    ]

    fields = "temperature_2m,wind_speed_10m,precipitation,weather_code,relative_humidity_2m"
    tasks = [
        _get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current={fields}&timezone=UTC"
        )
        for _, lat, lon in metro_coords
    ]
    noaa_t = _get("https://api.weather.gov/alerts/active?status=actual&message_type=alert&limit=5")

    results = await _gather(*tasks, noaa_t)
    wx_results, noaa_r = results[:-1], results[-1]

    cities = {}
    for (name, _, _), res in zip(metro_coords, wx_results):
        if _ok(res):
            c = res.get("current", {})
            cities[name] = {
                "temp_c": c.get("temperature_2m"),
                "humidity_pct": c.get("relative_humidity_2m"),
                "wind_kmh": c.get("wind_speed_10m"),
                "precip_mm": c.get("precipitation"),
                "code": c.get("weather_code"),
            }

    alerts = []
    if _ok(noaa_r):
        for f in (noaa_r.get("features") or [])[:5]:
            props = f.get("properties", {})
            alerts.append({
                "event": props.get("event"),
                "headline": (props.get("headline") or "")[:120],
                "severity": props.get("severity"),
                "area": props.get("areaDesc","")[:80],
            })

    return {"cities": cities, "us_active_alerts": alerts, "source": "Open-Meteo + NOAA"}

# ─────────────────────────────────────────────────────────────────────────────
# 8. CLIMATE — ClimateMonitor CO2/CH4/sea level + Open-Meteo AQ
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_climate():
    co2_t    = _get("https://climatemonitor.info/api/public/v1/co2/latest")
    ch4_t    = _get("https://climatemonitor.info/api/public/v1/ch4/latest")
    sl_t     = _get("https://climatemonitor.info/api/public/v1/sea-level/latest")
    temp_t   = _get("https://climatemonitor.info/api/public/v1/temperature/latest")

    co2_r, ch4_r, sl_r, temp_r = await _gather(co2_t, ch4_t, sl_t, temp_t)

    return {
        "co2_ppm": _ok(co2_r) and co2_r,
        "methane_ppb": _ok(ch4_r) and ch4_r,
        "sea_level_mm": _ok(sl_r) and sl_r,
        "temp_anomaly_c": _ok(temp_r) and temp_r,
        "source": "ClimateMonitor (NOAA + NASA)",
        "note": "CO2 and methane are atmospheric concentrations. Sea level is rise in mm vs baseline.",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 9. AIR QUALITY — OpenAQ + Open-Meteo air quality
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_air():
    openaq_t = _get(
        "https://api.openaq.org/v2/latest?limit=10&order_by=lastUpdated&sort=desc",
        headers={"Accept": "application/json"}
    )
    # Open-Meteo air quality for major cities
    aq_cities = [("New York", 40.71, -74.01), ("London", 51.51, -0.13), ("Beijing", 39.90, 116.39)]
    aq_tasks  = [
        _get(
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,european_aqi"
        )
        for _, lat, lon in aq_cities
    ]

    results = await _gather(openaq_t, *aq_tasks)
    openaq_r, *aq_results = results

    readings = []
    if _ok(openaq_r):
        for r in (openaq_r.get("results") or [])[:8]:
            for m in r.get("measurements", []):
                if m.get("parameter") in ("pm25","pm10","o3","no2","co"):
                    readings.append({
                        "location": r.get("name","")[:40],
                        "country": r.get("country",""),
                        "param": m["parameter"],
                        "value": m["value"],
                        "unit": m["unit"],
                    })

    city_aqi = {}
    for (name, _, _), res in zip(aq_cities, aq_results):
        if _ok(res):
            c = res.get("current", {})
            city_aqi[name] = {
                "pm2_5": c.get("pm2_5"),
                "pm10": c.get("pm10"),
                "no2": c.get("nitrogen_dioxide"),
                "ozone": c.get("ozone"),
                "european_aqi": c.get("european_aqi"),
            }

    return {"station_readings": readings[:10], "city_aqi": city_aqi, "source": "OpenAQ + Open-Meteo"}

# ─────────────────────────────────────────────────────────────────────────────
# 10. DISASTERS — USGS earthquakes + NOAA severe weather + hurricane warnings
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_disasters():
    quake_t     = _get(
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        "?format=geojson&minmagnitude=4.5&limit=15&orderby=time"
    )
    hurricane_t = _get("https://api.weather.gov/alerts/active?event=Hurricane+Warning")
    tornado_t   = _get("https://api.weather.gov/alerts/active?event=Tornado+Warning")
    flood_t     = _get("https://api.weather.gov/alerts/active?event=Flash+Flood+Warning")
    tsunami_t   = _get("https://api.weather.gov/alerts/active?event=Tsunami+Warning")

    quake_r, hurr_r, torn_r, flood_r, tsun_r = await _gather(quake_t, hurricane_t, tornado_t, flood_t, tsunami_t)

    quakes = []
    if _ok(quake_r):
        for f in (quake_r.get("features") or [])[:12]:
            p = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [None, None, None])
            quakes.append({
                "magnitude": p.get("mag"),
                "place": p.get("place","")[:80],
                "time": datetime.fromtimestamp(p.get("time", 0)/1000, tz=timezone.utc).isoformat(),
                "depth_km": coords[2],
                "lat": coords[1],
                "lon": coords[0],
                "url": p.get("url",""),
            })

    def parse_alerts(data):
        if not _ok(data):
            return []
        alerts = []
        for f in (data.get("features") or [])[:5]:
            p = f.get("properties", {})
            alerts.append({
                "event": p.get("event"),
                "severity": p.get("severity"),
                "area": p.get("areaDesc","")[:80],
                "headline": (p.get("headline") or "")[:100],
            })
        return alerts

    return {
        "earthquakes": quakes,
        "hurricane_warnings": parse_alerts(hurr_r),
        "tornado_warnings": parse_alerts(torn_r),
        "flash_flood_warnings": parse_alerts(flood_r),
        "tsunami_warnings": parse_alerts(tsun_r),
        "source": "USGS + NOAA",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 11. SPACE — ISS + astronauts + SpaceX + Launch Library + NASA APOD
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_space():
    iss_t       = _get("http://api.open-notify.org/iss-now.json")
    astros_t    = _get("http://api.open-notify.org/astros.json")
    spacex_t    = _get("https://api.spacexdata.com/v4/launches/next")
    launches_t  = _get("https://lldev.thespacedevs.com/2.2.0/launch/upcoming/?format=json&limit=5")
    apod_t      = _get(f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}")
    sunrise_t   = _get("https://api.sunrisesunset.io/json?lat=40.71&lng=-74.01&timezone=UTC")
    neo_t       = _get(f"https://api.nasa.gov/neo/rest/v1/feed?api_key={NASA_KEY}")

    iss_r, astros_r, spacex_r, launches_r, apod_r, sunrise_r, neo_r = await _gather(
        iss_t, astros_t, spacex_t, launches_t, apod_t, sunrise_t, neo_t
    )

    iss = None
    if _ok(iss_r):
        pos = iss_r.get("iss_position", {})
        iss = {"lat": float(pos.get("latitude",0)), "lon": float(pos.get("longitude",0))}

    astronauts = []
    if _ok(astros_r):
        astronauts = [{"name": p.get("name"), "craft": p.get("craft")} for p in astros_r.get("people",[])]

    spacex = None
    if _ok(spacex_r):
        spacex = {
            "mission": spacex_r.get("name"),
            "date_utc": spacex_r.get("date_utc"),
            "rocket": spacex_r.get("rocket"),
            "details": (spacex_r.get("details") or "")[:120],
        }

    upcoming = []
    if _ok(launches_r):
        for l in (launches_r.get("results") or [])[:5]:
            upcoming.append({
                "name": l.get("name"),
                "provider": l.get("launch_service_provider",{}).get("name"),
                "net": l.get("net"),
                "status": l.get("status",{}).get("name"),
            })

    apod = None
    if _ok(apod_r):
        apod = {
            "title": apod_r.get("title"),
            "date": apod_r.get("date"),
            "explanation": (apod_r.get("explanation") or "")[:200],
            "url": apod_r.get("url"),
        }

    sunrise = None
    if _ok(sunrise_r):
        d = sunrise_r.get("results", {})
        sunrise = {"sunrise": d.get("sunrise"), "sunset": d.get("sunset"), "solar_noon": d.get("solar_noon")}

    near_earth = []
    if _ok(neo_r):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for obj in list((neo_r.get("near_earth_objects") or {}).get(today, []))[:5]:
            cd = obj.get("close_approach_data",[{}])[0]
            near_earth.append({
                "name": obj.get("name"),
                "diameter_m": obj.get("estimated_diameter",{}).get("meters",{}).get("estimated_diameter_max"),
                "hazardous": obj.get("is_potentially_hazardous_asteroid"),
                "miss_distance_km": cd.get("miss_distance",{}).get("kilometers"),
                "velocity_kmh": cd.get("relative_velocity",{}).get("kilometers_per_hour"),
            })

    return {
        "iss_position": iss,
        "astronauts_in_space": astronauts,
        "spacex_next_launch": spacex,
        "upcoming_launches": upcoming,
        "nasa_apod": apod,
        "sunrise_sunset_nyc": sunrise,
        "near_earth_asteroids_today": near_earth,
        "source": "open-notify + SpaceX API + The Space Devs + NASA",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 12. SCIENCE — arXiv + PubMed + ClinicalTrials + Science RSS
# ─────────────────────────────────────────────────────────────────────────────
SCIENCE_FEEDS = [
    ("NASA News",         "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("Nature",            "https://www.nature.com/nature.rss"),
    ("Science Magazine",  "https://www.science.org/rss/news_current.xml"),
    ("New Scientist",     "https://www.newscientist.com/feed/home/"),
    ("Scientific American","https://rss.sciam.com/ScientificAmerican-Global"),
    ("ESA News",          "https://www.esa.int/rssfeed/Our_Activities/Space_Science"),
    ("arXiv CS.AI",       "http://export.arxiv.org/rss/cs.AI"),
    ("arXiv Physics",     "http://export.arxiv.org/rss/physics"),
]

async def fetch_science():
    rss_t    = _multi_rss(SCIENCE_FEEDS, limit_per_feed=4, total=25)
    pubmed_t = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=artificial+intelligence+medicine&retmax=5&retmode=json&sort=pub+date")
    trials_t = _get("https://clinicaltrials.gov/api/v2/studies?query.term=AI+cancer&pageSize=5&format=json")

    articles, pubmed_r, trials_r = await asyncio.gather(rss_t, pubmed_t, trials_t, return_exceptions=True)
    if isinstance(articles, Exception):
        articles = []

    pubmed_ids = []
    if _ok(pubmed_r):
        pubmed_ids = pubmed_r.get("esearchresult", {}).get("idlist", [])

    active_trials = []
    if _ok(trials_r):
        for study in (trials_r.get("studies") or [])[:5]:
            ps   = study.get("protocolSection", {})
            id_m = ps.get("identificationModule", {})
            st_m = ps.get("statusModule", {})
            active_trials.append({
                "nct_id": id_m.get("nctId"),
                "title":  (id_m.get("briefTitle") or "")[:100],
                "status": st_m.get("overallStatus"),
            })

    return {
        "articles": articles,
        "source_count": len(SCIENCE_FEEDS),
        "pubmed_recent_ids": pubmed_ids,
        "active_clinical_trials": active_trials,
    }

# ─────────────────────────────────────────────────────────────────────────────
# 13. MEDICAL — FDA recalls + WHO + Health RSS feeds
# ─────────────────────────────────────────────────────────────────────────────
MEDICAL_FEEDS = [
    ("WHO News",         "https://www.who.int/rss-feeds/news-english.xml"),
    ("CDC Newsroom",     "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("NIH News",         "https://www.nih.gov/news-events/news-releases/feed"),
    ("WebMD Health",     "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"),
    ("Medscape",         "https://www.medscape.com/cx/rssfeeds/2122.xml"),
    ("STAT News",        "https://www.statnews.com/feed/"),
    ("Health Affairs",   "https://www.healthaffairs.org/rss/site_5/41.xml"),
]

async def fetch_medical():
    rss_t    = _multi_rss(MEDICAL_FEEDS, limit_per_feed=4, total=25)
    drug_t   = _get("https://api.fda.gov/drug/enforcement.json?limit=5&sort=recall_initiation_date:desc")
    food_t   = _get("https://api.fda.gov/food/enforcement.json?limit=5&sort=recall_initiation_date:desc")
    device_t = _get("https://api.fda.gov/device/recall.json?limit=5&sort=event_date_initiated:desc")

    articles, drug_r, food_r, device_r = await asyncio.gather(rss_t, drug_t, food_t, device_t, return_exceptions=True)
    if isinstance(articles, Exception):
        articles = []

    def parse_recalls(data, date_field):
        if not _ok(data):
            return []
        return [{"product": (r.get("product_description","") or r.get("device_name",""))[:80],
                 "reason": (r.get("reason_for_recall","") or "")[:100],
                 "class": r.get("classification",""),
                 "date": r.get(date_field,"")} for r in (data.get("results") or [])]

    return {
        "articles": articles,
        "source_count": len(MEDICAL_FEEDS),
        "drug_recalls": parse_recalls(drug_r, "recall_initiation_date"),
        "food_recalls": parse_recalls(food_r, "recall_initiation_date"),
        "device_recalls": parse_recalls(device_r, "event_date_initiated"),
        "source": "WHO + CDC + NIH + OpenFDA",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 14. TECH — RSS from TechCrunch, Wired, Ars, The Verge, MIT Tech Review + APIs
# ─────────────────────────────────────────────────────────────────────────────
TECH_FEEDS = [
    ("TechCrunch",        "https://techcrunch.com/feed/"),
    ("Wired",             "https://www.wired.com/feed/rss"),
    ("Ars Technica",      "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",         "https://www.theverge.com/rss/index.xml"),
    ("MIT Tech Review",   "https://www.technologyreview.com/feed/"),
    ("HackerNews Best",   "https://news.ycombinator.com/rss"),
    ("Dev.to",            "https://dev.to/feed"),
    ("GitHub Blog",       "https://github.blog/feed/"),
    ("Stack Overflow Blog","https://stackoverflow.blog/feed/"),
    ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),
    ("CSS-Tricks",        "https://css-tricks.com/feed/"),
    ("A List Apart",      "https://alistapart.com/main/feed/"),
]

async def fetch_tech():
    articles = await _multi_rss(TECH_FEEDS, limit_per_feed=4, total=35)
    # Also grab npm/PyPI stats as structured data
    npm_t   = _get("https://api.npmjs.org/downloads/point/last-week/react")
    pypi_t  = _get("https://pypistats.org/api/packages/requests/recent")
    npm_r, pypi_r = await _gather(npm_t, pypi_t)
    return {
        "articles": articles,
        "source_count": len(TECH_FEEDS),
        "npm_react_downloads_7d": _ok(npm_r) and npm_r.get("downloads"),
        "pypi_requests_downloads_7d": _ok(pypi_r) and (pypi_r.get("data",{}).get("last_week")),
    }

# ─────────────────────────────────────────────────────────────────────────────
# 15. CYBERSECURITY — NVD CVEs + Shodan InternetDB
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_cybersecurity():
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    end   = today.strftime("%Y-%m-%dT23:59:59")

    cve_t = _get(
        f"https://services.nvd.nist.gov/rest/json/cves/2.0"
        f"?pubStartDate={start}&pubEndDate={end}&resultsPerPage=15"
    )

    cve_r = await asyncio.gather(cve_t, return_exceptions=True)
    cve_r = cve_r[0]

    cves = []
    if _ok(cve_r):
        for vuln in (cve_r.get("vulnerabilities") or [])[:15]:
            cve = vuln.get("cve", {})
            descs = cve.get("descriptions", [{}])
            desc  = next((d["value"] for d in descs if d.get("lang") == "en"), "")[:200]
            metrics = cve.get("metrics", {})
            cvss = None
            for k in ["cvssMetricV31","cvssMetricV30","cvssMetricV2"]:
                if metrics.get(k):
                    cvss = metrics[k][0].get("cvssData",{}).get("baseScore")
                    break
            cves.append({
                "id": cve.get("id"),
                "description": desc,
                "cvss_score": cvss,
                "published": cve.get("published","")[:10],
            })

    return {
        "cves_published_today": cves,
        "count": len(cves),
        "source": "NVD (NIST)",
        "note": "CVEs published in the last 24 hours. CVSS score: 0-10 (10 = critical).",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 16. SPORTS — TheSportsDB + ESPN hidden API
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_sports():
    epl_t  = _get("https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4328")
    nba_t  = _get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
    nfl_t  = _get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
    soccer_t = _get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard")

    epl_r, nba_r, nfl_r, soccer_r = await _gather(epl_t, nba_t, nfl_t, soccer_t)

    epl = []
    if _ok(epl_r):
        for e in (epl_r.get("events") or [])[:5]:
            epl.append({
                "home": e.get("strHomeTeam"), "away": e.get("strAwayTeam"),
                "score": f"{e.get('intHomeScore','?')}-{e.get('intAwayScore','?')}",
                "date": e.get("dateEvent"),
            })

    def parse_espn(data, sport):
        if not _ok(data):
            return []
        games = []
        for ev in (data.get("events") or [])[:6]:
            comps = ev.get("competitions", [{}])[0]
            teams = comps.get("competitors", [])
            scores = {t.get("homeAway"): {"team": t.get("team",{}).get("displayName"), "score": t.get("score")} for t in teams}
            games.append({
                "home": scores.get("home",{}).get("team"), "home_score": scores.get("home",{}).get("score"),
                "away": scores.get("away",{}).get("team"), "away_score": scores.get("away",{}).get("score"),
                "status": comps.get("status",{}).get("type",{}).get("description",""),
            })
        return games

    return {
        "premier_league_recent": epl,
        "nba": parse_espn(nba_r, "nba"),
        "nfl": parse_espn(nfl_r, "nfl"),
        "epl_live": parse_espn(soccer_r, "soccer"),
        "source": "TheSportsDB + ESPN",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 17. GAMING — Steam player counts for top games
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_gaming():
    top_games = [
        ("Dota 2", 570), ("CS2", 730), ("PUBG", 578080),
        ("Apex Legends", 1172470), ("Rust", 252490),
        ("GTA V", 271590), ("Elden Ring", 1245620),
        ("Baldur's Gate 3", 1086940), ("Palworld", 1623730),
    ]

    tasks = [
        _get(f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}")
        for _, appid in top_games
    ]
    results = await _gather(*tasks)

    games = []
    for (name, appid), res in zip(top_games, results):
        count = None
        if _ok(res):
            count = res.get("response", {}).get("player_count")
        games.append({"game": name, "appid": appid, "players_live": count})

    games.sort(key=lambda x: x.get("players_live") or 0, reverse=True)
    return {"live_player_counts": games, "source": "Steam Web API"}

# ─────────────────────────────────────────────────────────────────────────────
# 18. SOCIAL — Reddit + Wikipedia trending + Bluesky + Dev.to
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_social():
    reddit_all_t  = _get("https://www.reddit.com/r/all/hot.json?limit=10")
    reddit_tech_t = _get("https://www.reddit.com/r/technology/hot.json?limit=8")
    wiki_t        = _get(
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2026/08/all-days"
    )

    reddit_all_r, reddit_tech_r, wiki_r = await _gather(reddit_all_t, reddit_tech_t, wiki_t)

    def parse_reddit(data, limit=6):
        if not _ok(data):
            return []
        posts = []
        for p in (data.get("data",{}).get("children") or []):
            d = p.get("data",{})
            if not d.get("stickied"):
                posts.append({
                    "title": d.get("title","")[:120],
                    "subreddit": d.get("subreddit"),
                    "score": d.get("score"),
                    "comments": d.get("num_comments"),
                })
        return posts[:limit]

    wiki_top = []
    if _ok(wiki_r):
        try:
            articles = wiki_r["items"][0]["articles"][:10]
            wiki_top = [{"title": a["article"].replace("_"," "), "views": a["views"], "rank": a["rank"]} for a in articles]
        except Exception:
            pass

    return {
        "reddit_all_hot": parse_reddit(reddit_all_r),
        "reddit_tech_hot": parse_reddit(reddit_tech_r),
        "wikipedia_top_articles": wiki_top,
        "source": "Reddit + Wikimedia",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 19. POLITICS — RSS from major political sources + GDELT
# ─────────────────────────────────────────────────────────────────────────────
POLITICS_FEEDS = [
    ("Reuters Politics",   "https://feeds.reuters.com/reuters/politicsNews"),
    ("AP Politics",        "https://feeds.apnews.com/rss/apf-politics"),
    ("BBC Politics",       "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("The Guardian Pol.",  "https://www.theguardian.com/politics/rss"),
    ("Politico",           "https://rss.politico.com/politics-news.xml"),
    ("The Hill",           "https://thehill.com/homenews/feed/"),
    ("Roll Call",          "https://rollcall.com/feed/"),
    ("Foreign Policy",     "https://foreignpolicy.com/feed/"),
    ("Al Jazeera",         "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Axios Politics",     "https://api.axios.com/feed/"),
    ("Reddit Politics",    "https://www.reddit.com/r/politics/.rss"),
    ("Reddit WorldPol",    "https://www.reddit.com/r/worldpolitics/.rss"),
]

async def fetch_politics():
    articles = await _multi_rss(POLITICS_FEEDS, limit_per_feed=4, total=35)
    # GDELT for global tone/events
    gdelt_t = _get(
        "https://api.gdeltproject.org/api/v2/doc/doc?query=politics&mode=artlist&maxrecords=8&format=json&timespan=24H"
    )
    gdelt_r = (await _gather(gdelt_t))[0]
    gdelt = []
    if _ok(gdelt_r):
        for a in (gdelt_r.get("articles") or [])[:8]:
            gdelt.append({"title": (a.get("title") or "")[:100], "url": a.get("url",""), "domain": a.get("domain",""), "tone": a.get("tone")})
    return {"articles": articles, "gdelt_global": gdelt, "source_count": len(POLITICS_FEEDS)}

# ─────────────────────────────────────────────────────────────────────────────
# 20. AVIATION — OpenSky Network live flights
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_aviation():
    # OpenSky — no key, global state
    opensky_t = _get(
        "https://opensky-network.org/api/states/all"
        "?lamin=24&lomin=-130&lamax=60&lomax=-60"  # continental USA + parts
    )
    density_t = _get("https://globe.adsbexchange.com/globeRates.json")

    opensky_r, density_r = await _gather(opensky_t, density_t)

    flights = []
    if _ok(opensky_r):
        states = opensky_r.get("states") or []
        for s in states[:20]:
            if s and len(s) >= 9:
                flights.append({
                    "callsign": (s[1] or "").strip(),
                    "origin_country": s[2],
                    "lat": s[6],
                    "lon": s[5],
                    "altitude_m": s[7],
                    "velocity_ms": s[9],
                    "heading": s[10],
                    "on_ground": s[8],
                })
        flights = [f for f in flights if f["callsign"] and not f["on_ground"]][:15]

    return {
        "total_airborne_usa": len(opensky_r.get("states") or []) if _ok(opensky_r) else None,
        "sample_flights": flights,
        "global_density": _ok(density_r) and density_r,
        "source": "OpenSky Network + ADS-B Exchange",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 21. JOBS — Remotive + BLS unemployment
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_jobs():
    remotive_t = _get("https://remotive.com/api/remote-jobs?category=software-dev&limit=10")
    bls_t      = _get("https://api.bls.gov/publicAPI/v1/timeseries/data/LNS14000000")

    remotive_r, bls_r = await _gather(remotive_t, bls_t)

    jobs = []
    if _ok(remotive_r):
        for j in (remotive_r.get("jobs") or [])[:10]:
            jobs.append({
                "title": j.get("title","")[:80],
                "company": j.get("company_name",""),
                "tags": (j.get("tags") or [])[:4],
                "salary": j.get("salary",""),
                "posted": j.get("publication_date","")[:10],
                "url": j.get("url",""),
            })

    unemployment = None
    if _ok(bls_r):
        try:
            d = bls_r["Results"]["series"][0]["data"][0]
            unemployment = {"rate_pct": float(d["value"]), "period": f"{d['periodName']} {d['year']}", "source": "BLS"}
        except Exception:
            pass

    return {
        "remote_dev_jobs": jobs,
        "us_unemployment": unemployment,
        "source": "Remotive + BLS",
    }

# ─────────────────────────────────────────────────────────────────────────────
# 22. COMMODITIES — Gold/Silver/Oil via Yahoo Finance
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_commodities():
    symbols = {
        "GC=F": "Gold (USD/oz)",
        "SI=F": "Silver (USD/oz)",
        "CL=F": "WTI Crude Oil (USD/bbl)",
        "BZ=F": "Brent Crude (USD/bbl)",
        "NG=F": "Natural Gas (USD/MMBtu)",
        "ZW=F": "Wheat (USD/bu)",
        "ZC=F": "Corn (USD/bu)",
        "HG=F": "Copper (USD/lb)",
    }
    tasks = [
        _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d")
        for sym in symbols
    ]
    results = await _gather(*tasks)

    prices = {}
    for (sym, label), res in zip(symbols.items(), results):
        if _ok(res):
            try:
                meta   = res["chart"]["result"][0]["meta"]
                price  = meta.get("regularMarketPrice")
                prev   = meta.get("previousClose") or meta.get("chartPreviousClose")
                change = round(((price - prev) / prev) * 100, 2) if price and prev else None
                prices[sym] = {"label": label, "price": price, "change_pct": change, "currency": meta.get("currency")}
            except Exception:
                pass

    return {"commodities": prices, "source": "Yahoo Finance futures"}

# ─────────────────────────────────────────────────────────────────────────────
# FEED MAP
# ─────────────────────────────────────────────────────────────────────────────
FEED_MAP = {
    "crypto":        (fetch_crypto,       60),
    "onchain":       (fetch_onchain,      30),
    "defi":          (fetch_defi,         300),
    "finance":       (fetch_finance,      120),
    "economics":     (fetch_economics,    86400),
    "news":          (fetch_news,         300),
    "weather":       (fetch_weather,      600),
    "climate":       (fetch_climate,      3600),
    "air":           (fetch_air,          600),
    "disasters":     (fetch_disasters,    300),
    "space":         (fetch_space,        1800),
    "science":       (fetch_science,      3600),
    "medical":       (fetch_medical,      3600),
    "tech":          (fetch_tech,         300),
    "cybersecurity": (fetch_cybersecurity,3600),
    "sports":        (fetch_sports,       120),
    "gaming":        (fetch_gaming,       300),
    "social":        (fetch_social,       300),
    "politics":      (fetch_politics,     600),
    "aviation":      (fetch_aviation,     60),
    "jobs":          (fetch_jobs,         3600),
    "commodities":   (fetch_commodities,  120),
}

# ══════════════════════════════════════════════════════════════════════════════
# DATA ROUTES
# ══════════════════════════════════════════════════════════════════════════════

async def resolve_user_from_key(api_key: str, db) -> Optional[dict]:
    kh = hash_key(api_key)
    async with db.execute("SELECT user_id FROM api_keys WHERE key_hash=?", (kh,)) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    uid = row["user_id"]
    await db.execute(
        "UPDATE api_keys SET last_used=? WHERE key_hash=?",
        (datetime.now(timezone.utc).isoformat(), kh)
    )
    await db.commit()
    async with db.execute("SELECT * FROM users WHERE id=?", (uid,)) as cur:
        user = await cur.fetchone()
    return dict(user) if user else None

@app.get("/data/feed/{category}")
async def get_feed(category: str, request: Request, db=Depends(get_db)):
    api_key = (
        request.headers.get("X-Pulse-Key") or
        request.query_params.get("key") or
        request.headers.get("Authorization","").removeprefix("Bearer ").strip()
    )

    if not api_key:
        if category not in ("crypto", "weather"):
            raise HTTPException(401, "API key required. Sign up at pulse.dev")
    else:
        user = await resolve_user_from_key(api_key, db)
        if not user:
            raise HTTPException(401, "Invalid API key")
        async with db.execute(
            "SELECT enabled FROM user_categories WHERE user_id=? AND category=?",
            (user["id"], category)
        ) as cur:
            row = await cur.fetchone()
        if row and not row["enabled"]:
            raise HTTPException(403, f"Category '{category}' is disabled in your settings")

    if category not in FEED_MAP:
        raise HTTPException(404, f"Unknown category '{category}'. Available: {list(FEED_MAP.keys())}")

    fetch_fn, ttl = FEED_MAP[category]
    data = await _cached(category, ttl, fetch_fn)
    return {
        "category": category,
        "label": CATEGORIES.get(category, {}).get("label", category),
        "data": data,
        "cached": category in _cache,
        "ttl_seconds": ttl,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/data/categories")
async def public_categories():
    return {k: {"label": v["label"], "icon": v["icon"], "desc": v["desc"]} for k, v in CATEGORIES.items()}

@app.get("/health")
async def health():
    return {"service": "pulse-auth", "status": "ok", "version": "0.3.0", "categories": len(FEED_MAP), "sources": "80+"}
