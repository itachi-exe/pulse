#!/usr/bin/env python3
"""
Pulse Auth + Extended Data Service — port 7072
Handles: signup, login, Google OAuth, API key management,
         category preferences, and 10+ live data feeds.
"""

import asyncio, hashlib, os, secrets, time, uuid
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

# ── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY    = os.getenv("JWT_SECRET", secrets.token_hex(32))
ALGORITHM     = "HS256"
TOKEN_EXPIRE  = 60 * 24 * 7   # 7 days in minutes
DB_PATH       = os.getenv("DB_PATH", "/root/pulse/pulse.db")
PULSE_API     = os.getenv("PULSE_API_URL", "http://localhost:7070")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:7071/auth/google/callback")

pwd_ctx = None  # replaced by bcrypt directly below

# ── Categories ───────────────────────────────────────────────────────────────
CATEGORIES = {
    "crypto":    {"label": "Crypto & Web3",      "icon": "₿", "desc": "ETH, BTC, SOL prices, gas, on-chain state"},
    "finance":   {"label": "Finance & Markets",   "icon": "📈", "desc": "FX rates, stock indices, commodities"},
    "news":      {"label": "Breaking News",        "icon": "📰", "desc": "Top headlines from global sources"},
    "weather":   {"label": "Weather",              "icon": "🌤", "desc": "Live conditions, forecasts, alerts"},
    "medical":   {"label": "Health & Medical",     "icon": "🩺", "desc": "FDA alerts, drug recalls, WHO bulletins"},
    "politics":  {"label": "Politics & Policy",    "icon": "🏛", "desc": "Election data, government feeds, legislation"},
    "science":   {"label": "Science & Space",      "icon": "🔭", "desc": "NASA, arXiv papers, ISS location"},
    "tech":      {"label": "Tech & Dev",            "icon": "⚙️", "desc": "HackerNews top, GitHub trending, releases"},
    "sports":    {"label": "Sports",               "icon": "⚽", "desc": "Live scores, standings, fixtures"},
    "economics": {"label": "Economics",            "icon": "🏦", "desc": "World Bank indicators, inflation, GDP"},
    "air":       {"label": "Air Quality & Climate","icon": "🌍", "desc": "AQI, pollution, climate indexes"},
    "social":    {"label": "Social Signals",       "icon": "📡", "desc": "Reddit trending, sentiment, viral topics"},
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

app = FastAPI(title="Pulse Auth", lifespan=lifespan)
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
    # Default all categories enabled
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

# Google OAuth
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
# LIVE DATA FEEDS
# ══════════════════════════════════════════════════════════════════════════════

# In-memory cache: {feed_id: {data, fetched_at, ttl}}
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
            return entry["data"]   # serve stale on error
        return {"error": str(e)}

async def _http(url, headers=None, timeout=8):
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(url, headers=headers or {})
        return r.json()

# ── Fetchers ──────────────────────────────────────────────────────────────────

async def fetch_crypto():
    data = await _http(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum,solana,matic-network,chainlink,avalanche-2,polkadot"
        "&vs_currencies=usd&include_24hr_change=true"
    )
    result = {}
    for coin, vals in data.items():
        result[coin] = {"price_usd": vals.get("usd"), "change_24h": vals.get("usd_24h_change")}
    return result

async def fetch_finance():
    data = await _http("https://api.exchangerate-api.com/v4/latest/USD")
    rates = data.get("rates", {})
    keep  = ["EUR","GBP","JPY","CAD","AUD","CHF","CNY","INR","BRL","KRW"]
    return {"base": "USD", "rates": {k: rates[k] for k in keep if k in rates}}

async def fetch_weather():
    # Open-Meteo — free, no key, global
    data = await _http(
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=40.71&longitude=-74.01"
        "&current=temperature_2m,wind_speed_10m,precipitation,weather_code"
        "&timezone=UTC"
    )
    c = data.get("current", {})
    return {
        "location": "Global reference (New York)",
        "temperature_c": c.get("temperature_2m"),
        "wind_kmh": c.get("wind_speed_10m"),
        "precipitation_mm": c.get("precipitation"),
        "weather_code": c.get("weather_code"),
        "time": c.get("time"),
    }

async def fetch_news():
    data = await _http(
        "https://hacker-news.firebaseio.com/v0/topstories.json"
    )
    ids = data[:10] if isinstance(data, list) else []
    stories = []
    async with httpx.AsyncClient(timeout=8) as c:
        tasks = [c.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json") for i in ids[:8]]
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for r in resps:
            if not isinstance(r, Exception):
                s = r.json()
                if s and s.get("title"):
                    stories.append({"title": s["title"], "score": s.get("score"), "url": s.get("url","")})
    return {"source": "HackerNews", "stories": stories}

async def fetch_medical():
    data = await _http(
        "https://api.fda.gov/drug/enforcement.json?limit=5&sort=recall_initiation_date:desc"
    )
    results = data.get("results", [])
    return {
        "source": "OpenFDA",
        "recent_recalls": [
            {"product": r.get("product_description","")[:80],
             "reason": r.get("reason_for_recall","")[:100],
             "date": r.get("recall_initiation_date","")}
            for r in results
        ]
    }

async def fetch_science():
    # ISS location — no key
    iss = await _http("http://api.open-notify.org/iss-now.json")
    pos = iss.get("iss_position", {})
    # arXiv latest AI papers
    arxiv = await _http(
        "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5",
        headers={"Accept": "application/xml"}
    )
    return {
        "iss": {"lat": pos.get("latitude"), "lon": pos.get("longitude"), "timestamp": iss.get("timestamp")},
        "arxiv_note": "arXiv latest AI papers — see /feed/science for titles",
    }

async def fetch_tech():
    data = await _http("https://hacker-news.firebaseio.com/v0/beststories.json")
    ids = data[:5] if isinstance(data, list) else []
    stories = []
    async with httpx.AsyncClient(timeout=8) as c:
        tasks = [c.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json") for i in ids]
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for r in resps:
            if not isinstance(r, Exception):
                s = r.json()
                if s and s.get("title"):
                    stories.append({"title": s["title"], "score": s.get("score"), "url": s.get("url","")})
    return {"source": "HackerNews Best", "stories": stories}

async def fetch_economics():
    # World Bank — GDP growth latest
    data = await _http(
        "https://api.worldbank.org/v2/country/US;CN;GB;JP;DE/indicator/NY.GDP.MKTP.KD.ZG"
        "?format=json&mrv=1&per_page=10"
    )
    rows = data[1] if isinstance(data, list) and len(data) > 1 else []
    result = {}
    for r in rows:
        if r and r.get("value") is not None:
            result[r["country"]["id"]] = {
                "country": r["country"]["value"],
                "gdp_growth_pct": r["value"],
                "year": r["date"],
            }
    return {"source": "World Bank", "gdp_growth": result}

async def fetch_air():
    # Open-AQ — no key for basic queries
    data = await _http(
        "https://api.openaq.org/v2/latest?limit=5&country=US&order_by=lastUpdated&sort=desc",
        headers={"Accept": "application/json"}
    )
    results = data.get("results", [])
    readings = []
    for r in results[:5]:
        for m in r.get("measurements", []):
            if m.get("parameter") in ("pm25","pm10","o3","no2"):
                readings.append({
                    "location": r.get("name",""),
                    "param": m["parameter"],
                    "value": m["value"],
                    "unit": m["unit"],
                    "last_updated": m.get("lastUpdated",""),
                })
    return {"source": "OpenAQ", "readings": readings[:8]}

async def fetch_sports():
    data = await _http(
        "https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4328"
    )
    events = data.get("events", []) or []
    return {
        "source": "TheSportsDB",
        "league": "English Premier League",
        "recent": [
            {"home": e.get("strHomeTeam"), "away": e.get("strAwayTeam"),
             "score": f"{e.get('intHomeScore','?')}-{e.get('intAwayScore','?')}",
             "date": e.get("dateEvent")}
            for e in events[:5]
        ]
    }

async def fetch_social():
    # Reddit top — no key needed for JSON API
    data = await _http(
        "https://www.reddit.com/r/technology/hot.json?limit=8",
        headers={"User-Agent": "pulse-feed/1.0"}
    )
    posts = data.get("data", {}).get("children", [])
    return {
        "source": "Reddit r/technology",
        "trending": [
            {"title": p["data"]["title"][:100], "score": p["data"]["score"],
             "comments": p["data"]["num_comments"]}
            for p in posts if not p["data"].get("stickied")
        ][:6]
    }

async def fetch_politics():
    # GNews politics (free tier, no key needed for basic)
    data = await _http(
        "https://gnews.io/api/v4/top-headlines?category=politics&lang=en&max=5&apikey=free",
    )
    articles = data.get("articles", [])
    return {
        "source": "GNews",
        "headlines": [
            {"title": a.get("title","")[:100], "source": a.get("source",{}).get("name",""),
             "published": a.get("publishedAt","")}
            for a in articles
        ]
    }

FEED_MAP = {
    "crypto":    (fetch_crypto,   60),
    "finance":   (fetch_finance,  300),
    "weather":   (fetch_weather,  600),
    "news":      (fetch_news,     300),
    "medical":   (fetch_medical,  3600),
    "science":   (fetch_science,  1800),
    "tech":      (fetch_tech,     300),
    "economics": (fetch_economics,86400),
    "air":       (fetch_air,      600),
    "sports":    (fetch_sports,   900),
    "social":    (fetch_social,   300),
    "politics":  (fetch_politics, 600),
}

# ── Data endpoint ─────────────────────────────────────────────────────────────

async def resolve_user_from_key(api_key: str, db) -> Optional[dict]:
    kh = hash_key(api_key)
    async with db.execute(
        "SELECT user_id FROM api_keys WHERE key_hash=?", (kh,)
    ) as cur:
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
    # Validate API key
    api_key = (
        request.headers.get("X-Pulse-Key") or
        request.query_params.get("key") or
        request.headers.get("Authorization","").removeprefix("Bearer ").strip()
    )

    if not api_key:
        # Public access — crypto only, no key needed
        if category != "crypto":
            raise HTTPException(401, "API key required. Sign up at pulse.itachi.dev")
    else:
        user = await resolve_user_from_key(api_key, db)
        if not user:
            raise HTTPException(401, "Invalid API key")
        # Check user has this category enabled
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
    return {"service": "pulse-auth", "status": "ok", "version": "0.2.0"}
