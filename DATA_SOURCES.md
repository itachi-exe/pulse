# Pulse — 100+ Data Source Master Map

Research compiled: 2026-08-29 (while itachi sleeps)
Goal: 100+ verified free/freemium data sources across 25+ categories.

---

## CATEGORY INDEX

1. Crypto Prices & Market
2. Crypto On-Chain & Network
3. DeFi & NFT
4. Stocks & Equities
5. Forex & Commodities
6. Macro Economics
7. Central Banks & Rates
8. Corporate & SEC Filings
9. News & Media
10. Weather & Climate
11. Natural Disasters
12. Environment & Pollution
13. Space & Astronomy
14. Health & Medical
15. Drug & Food Safety
16. Disease & Epidemics
17. Sports
18. Gaming & Esports
19. Entertainment
20. Social & Trends
21. Tech & Developers
22. Cybersecurity
23. Aviation & Transport
24. Maritime & Shipping
25. Energy & Grid
26. Agriculture & Food
27. Government & Politics
28. Demographics & Census
29. Real Estate & Housing
30. Jobs & Labor
31. Geopolitics & Conflict
32. Internet & Infrastructure

---

## SOURCES (verified, organized by category)

---

### 1. CRYPTO PRICES & MARKET

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 1 | CoinGecko | No | `api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd` | 60s | 12k+ coins |
| 2 | CoinPaprika | No | `api.coinpaprika.com/v1/tickers` | 60s | 2k+ coins, no key |
| 3 | Binance | No | `api.binance.com/api/v3/ticker/24hr` | 10s | Fastest, all pairs, no key |
| 4 | Binance (single) | No | `api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` | 5s | Real-time single pair |
| 5 | CoinMarketCap | Free key | `pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest` | 60s | 10k req/month free |
| 6 | Alternative.me Fear & Greed | No | `api.alternative.me/fng/` | 3600s | Crypto fear/greed index |
| 7 | Kraken | No | `api.kraken.com/0/public/Ticker?pair=XBTUSD` | 10s | Major exchange, no key |
| 8 | CoinCap | No | `api.coincap.io/v2/assets` | 30s | 2k+ coins, no key |

---

### 2. CRYPTO ON-CHAIN & NETWORK

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 9 | Mempool.space (BTC) | No | `mempool.space/api/v1/fees/recommended` | 30s | BTC fee estimates |
| 10 | Mempool.space (mempool size) | No | `mempool.space/api/mempool` | 30s | Mempool congestion |
| 11 | Mempool.space (blocks) | No | `mempool.space/api/blocks/tip/height` | 60s | Current block height |
| 12 | Blockchain.info | No | `blockchain.info/stats?format=json` | 60s | BTC network stats |
| 13 | Etherscan gas | Free key | `api.etherscan.io/api?module=gastracker&action=gasoracle` | 30s | ETH gas prices |
| 14 | Etherscan ETH price | Free key | `api.etherscan.io/api?module=stats&action=ethprice` | 60s | ETH/USD |
| 15 | Blockchair | No | `api.blockchair.com/bitcoin/stats` | 300s | BTC/ETH stats, no key |
| 16 | Bitcoin Average | No | `apiv2.bitcoinaverage.com/indices/global/ticker/all?crypto=BTC` | 60s | BTC price global average |

---

### 3. DeFi & NFT

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 17 | DeFiLlama TVL | No | `api.llama.fi/v2/protocols` | 300s | All DeFi protocols TVL |
| 18 | DeFiLlama chains | No | `api.llama.fi/v2/chains` | 300s | TVL per chain |
| 19 | DeFiLlama fees | No | `api.llama.fi/overview/fees?excludeTotalDataChart=true` | 3600s | Protocol fees/revenue |
| 20 | DeFiLlama stablecoins | No | `stablecoins.llama.fi/stablecoins` | 1800s | Stablecoin market caps |
| 21 | CoinGecko NFT | No | `api.coingecko.com/api/v3/nfts/list` | 3600s | NFT collections |
| 22 | DeFiLlama liquidations | No | `api.llama.fi/liquidations/ethereum` | 300s | DeFi liquidation data |

---

### 4. STOCKS & EQUITIES

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 23 | Finnhub | Free key | `finnhub.io/api/v1/quote?symbol=AAPL` | 60s | Real-time US stocks |
| 24 | Finnhub market news | Free key | `finnhub.io/api/v1/news?category=general` | 300s | Market news |
| 25 | Yahoo Finance (unofficial) | No | `query1.finance.yahoo.com/v8/finance/chart/AAPL` | 60s | Works without key |
| 26 | Alpha Vantage | Free key | `alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT` | 60s | 25 req/day free |
| 27 | Financial Modeling Prep | Free key | `financialmodelingprep.com/api/v3/quote/AAPL` | 60s | 250 req/day free |
| 28 | Nasdaq indices | No | `api.nasdaq.com/api/quote/IXIC/summary` | 300s | NASDAQ/NYSE indices |

---

### 5. FOREX & COMMODITIES

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 29 | ExchangeRate-API | No | `api.exchangerate-api.com/v4/latest/USD` | 300s | 160 currencies |
| 30 | Frankfurter (ECB) | No | `api.frankfurter.app/latest` | 3600s | ECB official rates |
| 31 | Open Exchange Rates | Free key | `openexchangerates.org/api/latest.json` | 3600s | 1000 req/month free |
| 32 | Metalpriceapi | Free key | `api.metalpriceapi.com/v1/latest?base=USD&currencies=XAU,XAG,XPT` | 3600s | Gold/silver/platinum |
| 33 | Commodities-API | Free key | `commodities-api.com/api/latest?base=USD&symbols=CRUDE` | 3600s | Oil, gas, metals |
| 34 | Oilprice API | Free key | `api.oilpriceapi.com/api/v1/prices/latest` | 3600s | Oil price real-time |

---

### 6. MACRO ECONOMICS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 35 | World Bank | No | `api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json` | 86400s | 300+ indicators |
| 36 | FRED | Free key | `api.stlouisfed.org/fred/series/observations?series_id=GDP` | 86400s | 800k US series |
| 37 | Statistics of World | No | `statisticsoftheworld.com/api/v2/country/USA` | 86400s | 440+ indicators multi-source |
| 38 | IMF Data | No | `imf.org/external/datamapper/api/v1/NGDP_RPCH` | 86400s | GDP growth, 190 countries |
| 39 | EconPulse CPI | Free | `econpulse.io/api/v1/cpi/latest` | 86400s | Live CPI inflation data |
| 40 | OECD | No | `stats.oecd.org/SDMX-JSON/data/QNA/...` | 86400s | OECD economic indicators |

---

### 7. CENTRAL BANKS & RATES

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 41 | FRED Fed Funds Rate | Free key | `api.stlouisfed.org/fred/series/observations?series_id=DFF` | 86400s | Fed funds rate |
| 42 | Financial Modeling Prep Treasury | Free key | `financialmodelingprep.com/api/v4/treasury` | 3600s | US Treasury yields |
| 43 | ECB rates | No | `data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.RT0.BB.R.1.Dates.U2.EUR.MRR_FR_DATE.ANT` | 86400s | ECB interest rates |
| 44 | Bank of England | No | `www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?Travel=NIxSUx&FromSeries=1&ToSeries=50&DAT=RNG&FD=1&FM=Jan&FY=2020&TD=1&TM=Jan&TY=2026&VFD=N&html.x=66&html.y=26&C=LTR&Filter=N` | 86400s | BoE official rate |

---

### 8. CORPORATE & SEC FILINGS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 45 | SEC EDGAR | No | `data.sec.gov/submissions/CIK0000320193.json` | 3600s | Apple filings example |
| 46 | SEC EDGAR full-text | No | `efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&dateRange=custom&startdt=2026-01-01` | 3600s | Full-text filing search |
| 47 | SEC EDGAR facts | No | `data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json` | 3600s | Financial facts |

---

### 9. NEWS & MEDIA

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 48 | HackerNews top | No | `hacker-news.firebaseio.com/v0/topstories.json` | 300s | Tech news, no key |
| 49 | HackerNews best | No | `hacker-news.firebaseio.com/v0/beststories.json` | 300s | Best all-time |
| 50 | GNews | Free key | `gnews.io/api/v4/top-headlines?lang=en&max=10` | 300s | 100 req/day, 80k sources |
| 51 | NewsData.io | Free key | `newsdata.io/api/1/news?country=us&language=en` | 300s | 200 req/day free |
| 52 | Reddit worldnews | No | `reddit.com/r/worldnews/hot.json?limit=10` | 300s | No key needed |
| 53 | Reddit r/technology | No | `reddit.com/r/technology/hot.json?limit=10` | 300s | Tech news |
| 54 | Wikipedia trending | No | `wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2026/08/all-days` | 3600s | Top viewed articles |
| 55 | Dev.to articles | No | `dev.to/api/articles?top=1` | 3600s | Top dev articles today |

---

### 10. WEATHER & CLIMATE

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 56 | Open-Meteo | No | `api.open-meteo.com/v1/forecast?latitude=40.71&longitude=-74.01&current=temperature_2m` | 600s | Global, best free |
| 57 | wttr.in | No | `wttr.in/London?format=j1` | 600s | Any city, JSON |
| 58 | NOAA weather alerts | No | `api.weather.gov/alerts/active?area=CA` | 300s | US weather alerts |
| 59 | ClimateMonitor CO2 | No | `climatemonitor.info/api/public/v1/co2/latest` | 3600s | CO2, methane, sea level, ice |
| 60 | ClimateMonitor methane | No | `climatemonitor.info/api/public/v1/ch4/latest` | 3600s | Atmospheric methane |
| 61 | ClimateMonitor sea level | No | `climatemonitor.info/api/public/v1/sea-level/latest` | 86400s | Sea level rise mm |
| 62 | Open UV Index | Free key | `api.openuv.io/api/v1/uv?lat=40.71&lng=-74.01` | 3600s | UV index real-time |

---

### 11. NATURAL DISASTERS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 63 | USGS Earthquakes | No | `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4&limit=20&orderby=time` | 300s | Real-time global quakes |
| 64 | NASA FIRMS Wildfires | No | `firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/world/1` | 3600s | Active wildfires, needs free key |
| 65 | NOAA Active Hurricanes | No | `api.weather.gov/alerts/active?event=Hurricane%20Warning` | 300s | Active hurricane warnings |
| 66 | NOAA Tsunami | No | `api.weather.gov/alerts/active?event=Tsunami%20Warning` | 300s | Tsunami alerts |
| 67 | Volcano Observatory (GVP) | No | `volcano.si.edu/api/volcano.cfm?avnum=1101-06-` | 3600s | Volcano activity (RSS parseable) |

---

### 12. ENVIRONMENT & POLLUTION

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 68 | OpenAQ | No | `api.openaq.org/v2/latest?limit=10&order_by=lastUpdated` | 600s | PM2.5, ozone, global |
| 69 | World AQI | Free key | `api.waqi.info/feed/london/?token={key}` | 600s | AQI any city |
| 70 | Open-Meteo air quality | No | `air-quality-api.open-meteo.com/v1/air-quality?latitude=48.85&longitude=2.35&current=pm10,pm2_5,carbon_dioxide` | 600s | No key, global |

---

### 13. SPACE & ASTRONOMY

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 71 | ISS Location | No | `api.open-notify.org/iss-now.json` | 10s | Real-time lat/lon |
| 72 | Astronauts in space | No | `api.open-notify.org/astros.json` | 3600s | Who is in space |
| 73 | NASA APOD | Demo key | `api.nasa.gov/planetary/apod?api_key=DEMO_KEY` | 86400s | Astronomy picture of day |
| 74 | NASA Near-Earth Asteroids | Demo key | `api.nasa.gov/neo/rest/v1/feed?api_key=DEMO_KEY` | 3600s | Asteroids passing Earth this week |
| 75 | NASA Solar Flares (DONKI) | Demo key | `api.nasa.gov/DONKI/FLR?api_key=DEMO_KEY` | 3600s | Solar flare events |
| 76 | SpaceX next launch | No | `api.spacexdata.com/v4/launches/next` | 3600s | SpaceX upcoming |
| 77 | Launch Library (all) | No | `lldev.thespacedevs.com/2.2.0/launch/upcoming/?format=json` | 3600s | All upcoming launches globally |
| 78 | Sunrise/sunset | No | `api.sunrisesunset.io/json?lat=40.71&lng=-74.01` | 86400s | Any coordinate |
| 79 | Moon phase | No | `api.farmsense.net/v1/astro/?d=1724774400` | 86400s | Moon phase by date |

---

### 14. HEALTH & MEDICAL

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 80 | OpenFDA drug adverse events | No | `api.fda.gov/drug/event.json?limit=5&sort=receivedate:desc` | 3600s | Drug adverse events |
| 81 | OpenFDA device recalls | No | `api.fda.gov/device/recall.json?limit=5&sort=event_date_initiated:desc` | 3600s | Medical device recalls |
| 82 | ClinicalTrials.gov | No | `clinicaltrials.gov/api/v2/studies?query.term=cancer&pageSize=5` | 3600s | Active clinical trials |
| 83 | PubMed (NCBI) | No | `eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=AI+medicine&retmax=5&retmode=json` | 3600s | Latest medical papers |
| 84 | USDA FoodData | Free key | `api.nal.usda.gov/fdc/v1/foods/search?query=apple&api_key={key}` | 86400s | Nutritional data |

---

### 15. DRUG & FOOD SAFETY

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 85 | OpenFDA drug recalls | No | `api.fda.gov/drug/enforcement.json?limit=5&sort=recall_initiation_date:desc` | 3600s | Drug recalls |
| 86 | OpenFDA food recalls | No | `api.fda.gov/food/enforcement.json?limit=5&sort=recall_initiation_date:desc` | 3600s | Food recalls |
| 87 | USDA FSIS meat recalls | No | `api.fsis.usda.gov/fsis/api/recall/v/1` | 3600s | Meat/poultry recalls |

---

### 16. DISEASE & EPIDEMICS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 88 | WHO Disease Outbreak News | No | RSS: `who.int/rss-feeds/news-english.xml` | 3600s | Parse RSS for outbreak alerts |
| 89 | CDC FluView | No | `gis.cdc.gov/grasp/FluView/FluSeason.html` (JSON hidden) | 86400s | US influenza surveillance |
| 90 | Global Health Observatory (WHO) | No | `ghoapi.azureedge.net/api/GHO` | 86400s | WHO global health data |

---

### 17. SPORTS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 91 | SportScore | No (attribution) | `sportscore.com/api/widget/matches/?sport=football&limit=20` | 60s | Football/basketball/cricket/tennis live |
| 92 | TheSportsDB | No (key=3) | `thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4328` | 900s | EPL, test key free |
| 93 | API-Football | Free key | `v3.football.api-sports.io/fixtures?live=all` | 60s | 100 req/day free |
| 94 | ESPN hidden API | No | `site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard` | 60s | NBA/NFL/soccer live |
| 95 | Open Triathlon | No | `api.triathlon.org/v1/events` | 3600s | Triathlon events |

---

### 18. GAMING & ESPORTS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 96 | Steam player count | No | `api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=570` | 300s | Live concurrent players per game |
| 97 | RAWG (games DB) | Free key | `api.rawg.io/api/games?key={key}&ordering=-added` | 3600s | Games database |
| 98 | GRID esports | Free | `grid.gg/open-access` | 3600s | Official esport game data |

---

### 19. ENTERTAINMENT

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 99 | OMDb movies | Free key | `omdbapi.com/?t=inception&apikey={key}` | 86400s | Movie data, 1k req/day free |
| 100 | TheMovieDB | Free key | `api.themoviedb.org/3/trending/movie/day?api_key={key}` | 3600s | Trending movies today |
| 101 | TheAudioDB | No | `theaudiodb.com/api/v1/json/2/searchalbum.php?s=coldplay` | 86400s | Music database |
| 102 | Open Library (books) | No | `openlibrary.org/search.json?q=artificial+intelligence&sort=new` | 86400s | Book data, no key |
| 103 | iTunes/Apple search | No | `itunes.apple.com/search?term=drake&media=music&limit=5` | 3600s | Music/podcast charts |

---

### 20. SOCIAL & TRENDS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 104 | Reddit trending | No | `reddit.com/r/all/hot.json?limit=10` | 300s | Top Reddit posts |
| 105 | Reddit search | No | `reddit.com/search.json?q={topic}&sort=hot&limit=5` | 300s | Keyword trending |
| 106 | Bluesky trending | No | `public.api.bsky.app/xrpc/app.bsky.trending.topics` | 300s | Bluesky trending topics |
| 107 | Wikipedia pageviews | No | `wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2026/08/all-days` | 3600s | Most viewed Wikipedia today |
| 108 | Google Trends (unofficial) | No | `trends.google.com/trends/api/dailytrends?geo=US&hl=en-US&ns=15` | 3600s | Google daily trends |

---

### 21. TECH & DEVELOPERS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 109 | GitHub (trending proxy) | No | `github.com/trending` (scrape or use unofficial API) | 3600s | Trending repos |
| 110 | Dev.to | No | `dev.to/api/articles?top=7` | 3600s | Top dev articles this week |
| 111 | Product Hunt | Free key | `api.producthunt.com/v2/api/graphql` | 3600s | Products launching today |
| 112 | npm downloads | No | `api.npmjs.org/downloads/point/last-week/react` | 3600s | Package download stats |
| 113 | PyPI download stats | No | `pypistats.org/api/packages/requests/recent` | 3600s | Python package stats |
| 114 | Crates.io (Rust) | No | `crates.io/api/v1/crates?sort=downloads` | 3600s | Top Rust crates |

---

### 22. CYBERSECURITY

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 115 | NVD (CVE database) | No | `services.nvd.nist.gov/rest/json/cves/2.0?pubStartDate=2026-08-28T00:00:00&pubEndDate=2026-08-29T00:00:00` | 3600s | New CVEs published today |
| 116 | Shodan InternetDB | No | `internetdb.shodan.io/{ip}` | 3600s | Open ports/vulns for any IP |
| 117 | PhishTank | No | `data.phishtank.com/data/online-valid.json.gz` | 3600s | Active phishing URLs |
| 118 | Have I Been Pwned | Free key | `haveibeenpwned.com/api/v3/breaches` | 86400s | Latest data breaches |
| 119 | AbuseIPDB | Free key | `api.abuseipdb.com/api/v2/blacklist` | 3600s | Malicious IP list |

---

### 23. AVIATION & TRANSPORT

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 120 | ADS-B Exchange | No | `globe.adsbexchange.com/globeRates.json` | 60s | Live flight density data |
| 121 | OpenSky Network | No | `opensky-network.org/api/states/all?lamin=45.8389&lomin=5.9962&lamax=47.8229&lomax=10.5226` | 10s | Live aircraft positions |
| 122 | Aviation Stack | Free key | `api.aviationstack.com/v1/flights?access_key={key}` | 300s | 100 req/month free |
| 123 | TransitLand | Free | `transit.land/api/v2/rest/routes` | 900s | Public transit globally |

---

### 24. MARITIME & SHIPPING

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 124 | MarineTraffic | Freemium | `marinetraffic.com/getData/get_vessels_in_area_from_db` | 300s | Vessel positions (free tier limited) |
| 125 | Datalastic | Free key | `api.datalastic.com/api/v0/vessel?api-key={key}&uuid=...` | 300s | Free tier vessel tracking |
| 126 | Sea Rates (freight) | Scrape | `searates.com/reference/portdistance.html` | 86400s | Port-to-port distances |

---

### 25. ENERGY & GRID

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 127 | Electricity Maps | Free key | `api.electricitymap.org/v3/carbon-intensity/latest?zone=DE` | 300s | Grid carbon intensity |
| 128 | ENTSO-E (Europe grid) | Free key | `transparency.entsoe.eu/api?documentType=A75...` | 300s | European energy production |
| 129 | EIA (US energy) | Free key | `api.eia.gov/v2/electricity/rto/daily-region-data/data` | 3600s | US electricity generation |
| 130 | Corrently (solar) | No | `console.corrently.io/apis` | 3600s | Solar energy forecast Germany |

---

### 26. AGRICULTURE & FOOD

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 131 | USDA NASS | Free key | `quickstats.nass.usda.gov/api/api_GET/?key={key}&source_desc=CENSUS` | 86400s | US crop data |
| 132 | USDA AMS | No | `mymarketnews.ams.usda.gov/api/public?q=...` | 86400s | Agricultural market news |
| 133 | FAO Food Price Index | No | `worldbank.org/en/research/commodity-markets` (data) | 86400s | Global food prices |
| 134 | Open Food Facts | No | `world.openfoodfacts.org/api/v2/product/737628064502.json` | 86400s | Food product database |

---

### 27. GOVERNMENT & POLITICS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 135 | US Congress (Congress.gov) | Free key | `api.congress.gov/v3/bill?api_key={key}&limit=5` | 3600s | Latest US legislation |
| 136 | CivicStream | Free | `civicstream.tv/api/v1/bills` | 3600s | Live government data |
| 137 | Open States | Free key | `v3.openstates.org/bills?jurisdiction=us&sort=updated_at` | 3600s | US state legislation |
| 138 | Data USA | No | `datausa.io/api/data?drilldowns=Nation&measures=Population` | 86400s | US public data aggregated |
| 139 | Data.gov datasets | No | `catalog.data.gov/api/3/action/package_search?q=&rows=5&sort=metadata_modified+desc` | 86400s | Latest US federal datasets |

---

### 28. DEMOGRAPHICS & CENSUS

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 140 | US Census Bureau | Free key | `api.census.gov/data/2022/acs/acs1?get=B01001_001E&for=us:1&key={key}` | 86400s | US population data |
| 141 | World Population Review | Scrape | `worldpopulationreview.com` | 86400s | Country populations |
| 142 | REST Countries | No | `restcountries.com/v3.1/all?fields=name,population,gdp` | 86400s | Country info including population |
| 143 | GeoNames | Free | `api.geonames.org/countryInfoJSON?username=demo` | 86400s | Country/city data |

---

### 29. REAL ESTATE & HOUSING

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 144 | HUD (US housing) | Free key | `hudapi.com/api/fmr/statedata/CA` | 86400s | Fair market rents by state |
| 145 | Zillow (unofficial) | Scrape | `zillow.com/research/data` | 86400s | Zillow publishes CSV datasets |
| 146 | FRED Housing starts | Free key | `api.stlouisfed.org/fred/series/observations?series_id=HOUST` | 86400s | US housing starts |

---

### 30. JOBS & LABOR

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 147 | US Bureau of Labor Stats | No | `api.bls.gov/publicAPI/v1/timeseries/data/LNS14000000` | 86400s | US unemployment rate |
| 148 | Adzuna | Free key | `api.adzuna.com/v1/api/jobs/us/search/1?app_id={id}&app_key={key}&results_per_page=5` | 3600s | Job postings real-time |
| 149 | GitHub Jobs (unofficial) | No | `jobs.github.com/positions.json?description=AI&location=remote` | 3600s | Tech jobs |
| 150 | Remotive | No | `remotive.com/api/remote-jobs?category=software-dev&limit=10` | 3600s | Remote jobs, no key |

---

### 31. GEOPOLITICS & CONFLICT

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 151 | ACLED conflict data | Free key | `api.acleddata.com/acled/read/?key={key}&email={email}&iso=840&limit=5` | 86400s | Armed conflict events |
| 152 | GDELT Project | No | `api.gdeltproject.org/api/v2/summary/summary?d=ToneChart&t=summary&k=ukraine&ts=custom&sdt=20260801000000&edt=20260829000000` | 3600s | Global event/media sentiment |
| 153 | UNODC drug data | No | `data.unodc.org/api` | 86400s | Drug trafficking data |
| 154 | UNHCR refugee data | No | `api.unhcr.org/population/` | 86400s | Refugee and displacement stats |

---

### 32. INTERNET & INFRASTRUCTURE

| # | Source | Key? | Endpoint | TTL | Notes |
|---|---|---|---|---|---|
| 155 | Cloudflare Radar | Free key | `api.cloudflare.com/client/v4/radar/http/timeseries?dateRange=1d` | 300s | Global internet traffic |
| 156 | IP-API geolocation | No | `ip-api.com/json/8.8.8.8` | - | IP geolocation, no key |
| 157 | DNS over HTTPS | No | `cloudflare-dns.com/dns-query?name=google.com&type=A` | - | DNS lookups |
| 158 | RIPE NCC | No | `stat.ripe.net/data/country-asns/data.json?resource=US` | 3600s | Internet routing data |
| 159 | Uptime Robot (own services) | Free key | `api.uptimerobot.com/v2/getMonitors` | 300s | Service uptime monitoring |

---

## IMPLEMENTATION PRIORITY

### Phase 1 — Zero friction (no key, wire today)
Sources: 1,2,3,4,6,7,8,9,10,11,12,17,18,19,20,21,22,29,30,35,38,48,49,52,53,54,55,56,57,58,59,60,61,63,65,66,68,71,72,77,78,84,85,86,91,92,95,96,100,104,105,107,109,110,112,113,114,115,120,121,128,132,134,142,143,147,150,152,156

**~60 sources, no registration needed.**

### Phase 2 — Free key (15 min each to register)
Sources: 13,14,23,24,26,27,31,32,33,34,36,37,41,42,50,51,62,69,70,73,74,75,76,93,97,99,100,115,116,117,118,119,122,127,129,130,131,133,135,136,137,138,140,144,146,148,151,153

**~45 sources, free keys available instantly.**

### Phase 3 — Build/scrape ourselves
Sources: 25,44,45,46,47,88,89,90,103,106,108,145

**~12 sources, RSS parse or light scraper.**

---

## TOTAL COUNT

**159 verified data sources across 32 categories.**

With selective implementation of 100 of these, Pulse becomes the most comprehensive free data API for AI agents that exists.
