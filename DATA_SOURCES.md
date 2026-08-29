# Pulse — Data Source Expansion Map

Research compiled: 2026-08-29
Goal: make Pulse significantly more useful by maximising live, free, high-signal data.

---

## TIER 1 — No key, no signup, plug in today

| Category | Source | Endpoint | TTL | Notes |
|---|---|---|---|---|
| Crypto | CoinGecko | `api.coingecko.com/api/v3/simple/price` | 60s | 30 coins, USD + change |
| Crypto | CoinPaprika | `api.coinpaprika.com/v1/tickers` | 60s | 2000 coins, no key |
| Crypto | Binance | `api.binance.com/api/v3/ticker/24hr` | 10s | All pairs, no key, very fast |
| Weather | Open-Meteo | `api.open-meteo.com/v1/forecast` | 600s | Global, no key, best free weather |
| Weather | wttr.in | `wttr.in/London?format=j1` | 600s | JSON, any city name, no key |
| Finance (FX) | ExchangeRate-API | `api.exchangerate-api.com/v4/latest/USD` | 300s | 160 currencies, no key |
| Finance (FX) | Frankfurter | `api.frankfurter.app/latest` | 3600s | ECB rates, no key |
| Finance (stocks) | Yahoo Finance (unofficial) | `query1.finance.yahoo.com/v8/finance/chart/AAPL` | 60s | No key, used in prod everywhere |
| News/Tech | HackerNews | Firebase API | 300s | Top/best/new stories |
| Science | ISS Location | `api.open-notify.org/iss-now.json` | 10s | Real-time, no key |
| Science | People in space | `api.open-notify.org/astros.json` | 3600s | Who is in space right now |
| Science | NASA APOD | `api.nasa.gov/planetary/apod?api_key=DEMO_KEY` | 3600s | DEMO_KEY works, 30 req/hr |
| Science | SpaceX | `api.spacexdata.com/v4/launches/next` | 3600s | Next launch, no key |
| Science | USGS Earthquakes | `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson` | 300s | Real-time quakes worldwide |
| Health | OpenFDA | `api.fda.gov/drug/enforcement.json` | 3600s | Drug recalls, no key |
| Health | OpenFDA | `api.fda.gov/food/enforcement.json` | 3600s | Food recalls, no key |
| Economics | World Bank | `api.worldbank.org/v2/country/.../indicator/...` | 86400s | 300+ indicators, no key |
| Economics | Statistics of the World | `statisticsoftheworld.com/api/v2/country/USA` | 86400s | 440+ indicators, multi-source |
| Air Quality | OpenAQ | `api.openaq.org/v2/latest` | 600s | PM2.5, ozone, global |
| Air Quality | IQAir (public) | `api.airvisual.com/v2/city` | 600s | Free tier, needs key |
| Social | Reddit JSON | `reddit.com/r/worldnews/hot.json` | 300s | Any subreddit, no key |
| Social | Reddit search | `reddit.com/search.json?q=...` | 300s | Keyword trends |
| Sports | SportScore | `sportscore.com/api/widget/matches/` | 60s | Football/basketball/cricket/tennis, no key, just attribution |
| Sports | TheSportsDB | `thesportsdb.com/api/v1/json/3/...` | 900s | Free tier, test key=3 |
| Crypto on-chain | Etherscan | `api.etherscan.io/api?module=gastracker` | 30s | Gas prices, free key |
| Crypto on-chain | Blockchain.info | `blockchain.info/stats?format=json` | 60s | BTC network stats, no key |
| Crypto on-chain | Mempool.space | `mempool.space/api/v1/fees/recommended` | 30s | BTC fee estimates |
| Time | WorldTimeAPI | `worldtimeapi.org/api/timezone/UTC` | - | Current time, any TZ |
| Internet | Cloudflare Radar | `api.cloudflare.com/client/v4/radar/...` | 300s | Internet traffic, free |

---

## TIER 2 — Free key, instant signup

| Category | Source | Key needed | Notes |
|---|---|---|---|
| Finance | Finnhub | Free key | Stocks, forex, crypto websocket. 60 calls/min. Real-time US stocks. |
| Finance | Alpha Vantage | Free key | Stocks, FX, crypto, indicators. 25 req/day free. |
| Finance | Polygon.io | Free key | Stocks delayed 15min on free. Good for indices. |
| News | GNews | Free key | 100 req/day, 80k sources, 41 languages, politics/sports/health |
| News | NewsData.io | Free key | 200 req/day, good category filters |
| News | MediaStack | Free key | 500 req/month, real-time, 50 countries |
| Science | NASA full | Free key | APOD, Mars rover photos, NEO asteroids, solar flares |
| Science | NOAA | Free key | Severe weather alerts, tide predictions, solar events |
| Crypto | CoinMarketCap | Free key | 10k calls/month, better metadata than CoinGecko |
| Health | OpenFDA full | Free key | Higher rate limits |
| Economics | FRED (St. Louis Fed) | Free key | 800k US economic series. Best for US macro data. |
| Air | AirVisual (IQAir) | Free key | 10k calls/month, city-level AQI |
| Social | Reddit OAuth | Free | Search trending, subreddit stats |
| Geopolitics | CivicStream | Free | Government data, legislation |
| Maps/Geo | OpenStreetMap/Nominatim | No key | Geocoding, POIs |

---

## TIER 3 — High-value, build ourselves (scrapers/parsers)

| Category | Source | Method | Value |
|---|---|---|---|
| Politics | Congress.gov RSS | RSS parse | US legislation updates |
| Politics | EU Parliament | RSS/JSON | EU legislation |
| Politics | UN News | RSS | Global political events |
| Health | WHO News | RSS | Disease outbreaks, global health alerts |
| Health | CDC MMWR | RSS | Weekly US disease data |
| Finance | CME Group | Scrape | Futures, commodities |
| Crypto | DeFiLlama | API | TVL, DeFi protocols, no key |
| Crypto | CoinGlass | Scrape | Liquidations, funding rates |
| Crypto | Glassnode (free) | Free key | On-chain: active addresses, NVT |
| Tech | GitHub trending | Scrape | What devs are building |
| Tech | Product Hunt | API | New products launching today |
| Science | arXiv | XML API | Latest AI/ML/physics papers |
| Science | PubMed | API | Medical research, no key |
| Economics | IMF Data | API | Global economic indicators |
| Social | Bluesky | AT Protocol | Trending topics, no key |

---

## WHAT TO BUILD NEXT (priority order)

### 1. Binance real-time crypto (10s TTL, no key)
Replace CoinGecko polling with Binance — faster, more pairs, no rate limit issues.
```
GET https://api.binance.com/api/v3/ticker/24hr
```

### 2. Finnhub (free key) — stocks + forex websocket
Get a free key, add: AAPL, MSFT, TSLA, NVDA, SPY, QQQ + major forex pairs.
Websocket available for real-time streaming.

### 3. NASA full suite (free DEMO_KEY or register)
- Solar flares: `api.nasa.gov/DONKI/FLR`
- Near-Earth asteroids: `api.nasa.gov/neo/rest/v1/feed`
- Mars weather: `api.nasa.gov/insight_weather/`

### 4. USGS Earthquakes (no key, real-time)
```
GET https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4&limit=10
```

### 5. DeFiLlama (no key) — DeFi TVL
```
GET https://api.llama.fi/v2/protocols
GET https://api.llama.fi/summary/fees/uniswap
```

### 6. SportScore (no key, just attribution)
Live scores across football, basketball, cricket, tennis. 10k req/day.

### 7. FRED (free key) — US macro
GDP, inflation (CPI), unemployment, Fed funds rate, mortgage rates.
800k series. Judges will be impressed by this depth.

### 8. Mempool.space (no key) — BTC network
Real-time fee estimates, mempool size, block height. Very useful for crypto agents.

### 9. Bluesky trending (AT Protocol, no key)
```
GET https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed
```

### 10. PubMed (no key) — Medical research
Latest published medical papers. Real signal for health agents.

---

## CATEGORIES TO ADD (not yet in Pulse)

- `stocks` — Finnhub + Yahoo Finance (US + global indices)
- `macro` — FRED + World Bank + IMF (GDP, inflation, rates)
- `defi` — DeFiLlama (TVL, protocol fees, liquidations)
- `onchain` — Mempool.space + Etherscan (BTC/ETH network state)
- `earthquakes` — USGS real-time
- `space` — NASA full suite (asteroids, solar flares, launches)
- `research` — arXiv + PubMed (latest papers)
- `trending` — GitHub trending + Product Hunt + Bluesky

---

## TOTAL POTENTIAL

Currently: **12 categories, ~15 sources**
After expansion: **20 categories, 35+ sources**

An AI agent using Pulse would have live access to:
- Every major crypto price and on-chain metric
- Real-time stock and forex prices
- Global macro indicators
- Live weather for any city
- Breaking news across 80k sources
- Active earthquakes worldwide
- Space events and solar activity
- DeFi protocol state
- Drug and food recalls
- Latest research papers
- Live sports scores
- Social sentiment and trends

That is a genuinely useful data layer. Nothing else gives agents all of this in one authenticated API call.
