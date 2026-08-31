#!/usr/bin/env python3
"""Expansion pass: add large scalable REAL feed families, validate against the
runtime parse contract, MERGE with existing verified_feeds.json. Keep only
feeds that return >=1 live item right now.
"""
import asyncio, xml.etree.ElementTree as ET, httpx, json, sys
from collections import Counter

CAND = []  # (cat, label, url)
def add(cat,label,url): CAND.append((cat,label,url))

def gnews_topic(cat,label,topic):
    add(cat,label,f"https://news.google.com/rss/headlines/section/topic/{topic}?hl=en-US&gl=US&ceid=US:en")
def gnews_q(cat,label,q):
    add(cat,label,f"https://news.google.com/rss/search?q={q.replace(' ','%20').replace('&','%26')}&hl=en-US&gl=US&ceid=US:en")
def reddit(cat,sub):
    add(cat,f"r/{sub}",f"https://www.reddit.com/r/{sub}/.rss")
def se_tag(cat,site,tag):
    dom = {"stackoverflow":"stackoverflow.com","serverfault":"serverfault.com","superuser":"superuser.com",
           "mathoverflow":"mathoverflow.net"}.get(site, f"{site}.stackexchange.com")
    add(cat,f"SE {site}/{tag}",f"https://{dom}/feeds/tag/{tag}")

# --- FINANCE: S&P + big caps + tickers (Google News search per company) ------
COMPANIES = ["Apple","Microsoft","Nvidia","Amazon","Alphabet Google","Meta Platforms","Tesla","Berkshire Hathaway",
 "Eli Lilly","JPMorgan Chase","Visa","UnitedHealth","Exxon Mobil","Mastercard","Johnson & Johnson","Broadcom",
 "Procter Gamble","Home Depot","Costco","AbbVie","Merck","Chevron","Adobe","Salesforce","Coca-Cola","PepsiCo",
 "Bank of America","Netflix","Walmart","McDonalds","Oracle","Accenture","Cisco","Thermo Fisher","AMD","Intel",
 "Qualcomm","Texas Instruments","IBM","Walt Disney","Verizon","Comcast","Pfizer","Nike","Wells Fargo","Boeing",
 "Goldman Sachs","Morgan Stanley","Caterpillar","American Express","Starbucks","Uber","Airbnb","PayPal","Block Square",
 "Palantir","Snowflake","ServiceNow","Shopify","Spotify","Zoom","Twilio","Datadog","CrowdStrike","Cloudflare",
 "MongoDB","Coinbase","Robinhood","SoFi","Micron","Applied Materials","Lam Research","ASML","TSMC","Arm Holdings",
 "Dell","HP","Lenovo","Sony","Samsung Electronics","Toyota","Volkswagen","Ford Motor","General Motors","Rivian",
 "Lucid Motors","Ferrari","Stellantis","BP","Shell","TotalEnergies","ConocoPhillips","Schlumberger","Halliburton"]
for c in COMPANIES: gnews_q("finance", f"{c} stock", f"{c} stock")

# --- FINANCE macro/markets topics --------------------------------------------
FIN_TOPICS = ["S&P 500","Nasdaq","Dow Jones","Federal Reserve interest rates","US inflation","bond yields",
 "US dollar index","earnings season","IPO market","private equity","hedge funds","corporate bonds",
 "mortgage rates","housing market","consumer spending","jobs report","GDP growth","recession forecast",
 "European Central Bank","Bank of Japan","emerging markets","currency markets","commodities market",
 "dividend stocks","stock buybacks","venture capital funding","SPAC","short selling","options trading"]
for t in FIN_TOPICS: gnews_q("finance", t, t)

# --- CRYPTO: coins + topics ---------------------------------------------------
COINS = ["Bitcoin","Ethereum","Solana","XRP Ripple","Cardano","Dogecoin","Polygon","Avalanche","Chainlink",
 "Polkadot","Litecoin","Uniswap","Cosmos","Stellar","Monero","Aave","Arbitrum","Optimism","Sui blockchain",
 "Aptos","Toncoin","Shiba Inu","Pepe coin","Bitcoin Cash","Filecoin","Injective","Sei network","Celestia"]
for c in COINS: gnews_q("crypto", c, f"{c} crypto")
CRYPTO_TOPICS = ["Bitcoin ETF","Ethereum staking","crypto regulation SEC","stablecoin","DeFi protocol",
 "NFT market","crypto hack exploit","Coinbase Binance","crypto mining","Bitcoin halving","Layer 2 scaling",
 "crypto adoption","central bank digital currency","Tether USDT","tokenization real world assets"]
for t in CRYPTO_TOPICS: gnews_q("crypto", t, t)
for s in ["CryptoCurrency","Bitcoin","ethereum","CryptoMarkets","defi","solana","CardanoCoin","Ripple",
          "dogecoin","litecoin","Monero","BitcoinBeginners","altcoin","CryptoTechnology","ethtrader"]:
    reddit("crypto", s)

# --- TECH: companies, topics, subreddits, SE tags ----------------------------
TECH_TOPICS = ["artificial intelligence","large language models","OpenAI ChatGPT","Google Gemini","Anthropic Claude",
 "generative AI","AI regulation","machine learning research","computer vision","autonomous vehicles","robotics",
 "quantum computing","semiconductor industry","cloud computing AWS Azure","cybersecurity breach","data privacy",
 "5G networks","augmented reality","virtual reality","metaverse","Internet of Things","edge computing",
 "open source software","developer tools","programming languages","Rust programming","Python programming",
 "Kubernetes","serverless","DevOps","API economy","SaaS startups","tech layoffs","electric vehicles battery",
 "space technology","biotech startups","fintech","chip manufacturing TSMC","Nvidia GPU","Apple Vision Pro"]
for t in TECH_TOPICS: gnews_q("tech", t, t)
for s in ["technology","programming","MachineLearning","artificial","LocalLLaMA","OpenAI","compsci","coding",
          "webdev","javascript","Python","rust","golang","devops","kubernetes","aws","selfhosted","homelab",
          "hardware","buildapc","gadgets","Futurology","singularity","datascience","dataengineering","java",
          "csharp","cpp","linux","opensource","sysadmin","networking","reverseengineering"]:
    reddit("tech", s)
for tag in ["python","javascript","java","c%23","rust","go","typescript","react","node.js","docker","kubernetes",
            "machine-learning","tensorflow","pytorch","sql","aws","azure","linux","git","c%2b%2b"]:
    se_tag("tech","stackoverflow",tag)

# --- CYBERSECURITY ------------------------------------------------------------
CYBER = ["ransomware attack","data breach","zero-day vulnerability","phishing campaign","malware","DDoS attack",
 "supply chain attack","critical infrastructure security","nation-state hackers","CVE vulnerability","APT group",
 "cloud security","endpoint security","identity theft","cyber espionage","dark web","cryptojacking",
 "software supply chain","OT ICS security","password breach"]
for t in CYBER: gnews_q("cybersecurity", t, t)
for s in ["cybersecurity","netsec","hacking","Malware","ReverseEngineering","AskNetsec","blueteamsec","privacy",
          "cybersecurity101","antivirus","pwned","security","ComputerSecurity"]:
    reddit("cybersecurity", s)

# --- MEDICAL / HEALTH ---------------------------------------------------------
MED = ["COVID-19","influenza outbreak","measles outbreak","cancer research","Alzheimer's disease","diabetes",
 "obesity","mental health","vaccine development","FDA drug approval","clinical trial","gene therapy","CRISPR",
 "antibiotic resistance","public health emergency","WHO health alert","heart disease","stroke","opioid crisis",
 "maternal health","pandemic preparedness","Ebola","malaria","tuberculosis","HIV AIDS","monkeypox mpox",
 "avian flu H5N1","drug shortage","medical device recall","telemedicine","obesity drug Ozempic","longevity research"]
for t in MED: gnews_q("medical", t, t)
for s in ["medicine","Health","publichealth","medical","science","COVID19","Coronavirus","AskDocs","nursing",
          "healthcare","cancer","mentalhealth","Epidemiology","biology","genetics","Nootropics"]:
    reddit("medical", s)

# --- POLITICS / WORLD ---------------------------------------------------------
POL = ["US elections","US Congress","Supreme Court","White House policy","European Union politics","UK Parliament",
 "United Nations","NATO","US China relations","Russia Ukraine war","Middle East conflict","Israel Gaza",
 "Iran nuclear","North Korea","immigration policy","trade tariffs","climate policy","US Senate","US House",
 "Brexit","France politics","Germany politics","India politics","Brazil politics","African Union","G7 summit",
 "G20 summit","sanctions","diplomacy","geopolitics"]
for t in POL: gnews_q("politics", t, t)
for s in ["politics","worldnews","geopolitics","PoliticalDiscussion","Ask_Politics","moderatepolitics",
          "neutralpolitics","internationalpolitics","europe","ukpolitics","AmericanPolitics","Economics"]:
    reddit("politics", s)

# --- NEWS: countries + world cities ------------------------------------------
COUNTRIES = ["United States","China","India","Japan","Germany","United Kingdom","France","Italy","Canada",
 "Brazil","Russia","Australia","Mexico","Indonesia","Saudi Arabia","Turkey","Netherlands","Switzerland",
 "Spain","South Korea","Nigeria","Egypt","Argentina","South Africa","Poland","Sweden","Norway","Israel",
 "Ukraine","Pakistan","Bangladesh","Vietnam","Philippines","Thailand","Malaysia","Singapore","UAE","Qatar",
 "Kenya","Ethiopia","Ghana","Morocco","Greece","Portugal","Ireland","Denmark","Finland","Austria","Belgium",
 "Czech Republic","Colombia","Chile","Peru","Venezuela"]
for c in COUNTRIES: gnews_q("news", f"{c} news", f"{c}")
for s in ["worldnews","news","UpliftingNews","nottheonion","anime_titties","inthenews","worldevents","globalnews"]:
    reddit("news", s)

# --- SCIENCE ------------------------------------------------------------------
SCI = ["physics discovery","astronomy telescope","black hole","exoplanet","climate science","genetics genome",
 "neuroscience brain","paleontology fossil","materials science","fusion energy","particle physics CERN",
 "marine biology","ecology biodiversity","volcano geology","chemistry research","nanotechnology","evolution",
 "archaeology discovery","renewable energy science","battery technology"]
for t in SCI: gnews_q("science", t, t)
for s in ["science","askscience","EverythingScience","physics","chemistry","biology","space","Astronomy",
          "geology","Paleontology","neuro","genetics","materials","energy","Physics_AWT"]:
    reddit("science", s)

# --- SPACE --------------------------------------------------------------------
SPACE = ["NASA mission","SpaceX launch","Artemis Moon","Mars rover","James Webb telescope","asteroid","satellite",
 "rocket launch","International Space Station","Blue Origin","space debris","solar flare","Starlink","lunar mission",
 "Europa Clipper","space tourism","Chinese space program","ESA mission","Voyager","exoplanet discovery"]
for t in SPACE: gnews_q("space", t, t)
for s in ["space","spacex","nasa","SpaceXLounge","astronomy","cosmology","Astronomy","spaceflight","rocketry"]:
    reddit("space", s)

# --- SPORTS -------------------------------------------------------------------
SPORTS = ["Premier League","Champions League","La Liga","NBA","NFL","MLB","NHL","Formula 1","tennis Grand Slam",
 "Olympics","World Cup soccer","cricket","golf PGA","UFC MMA","boxing","cycling Tour de France","rugby",
 "Serie A","Bundesliga","MLS soccer"]
for t in SPORTS: gnews_q("sports", t, t)
for s in ["sports","soccer","nba","nfl","baseball","hockey","formula1","tennis","MMA","boxing","Cricket",
          "golf","running","cycling","MLS","PremierLeague","reddevils","Gunners"]:
    reddit("sports", s)

# --- GAMING -------------------------------------------------------------------
GAMING = ["video game release","PlayStation 5","Xbox Series","Nintendo Switch","Steam PC gaming","esports",
 "game industry layoffs","indie games","GTA 6","Call of Duty","game console sales","cloud gaming","VR gaming",
 "mobile gaming","game awards"]
for t in GAMING: gnews_q("gaming", t, t)
for s in ["gaming","Games","pcgaming","PS5","XboxSeriesX","NintendoSwitch","Steam","esports","GlobalOffensive",
          "leagueoflegends","DotA2","valorant","EldenRing","BaldursGate3","Minecraft","truegaming"]:
    reddit("gaming", s)

# --- CLIMATE / ENERGY ---------------------------------------------------------
CLIMATE = ["climate change","global warming","carbon emissions","renewable energy","solar power","wind energy",
 "electric vehicles","COP climate summit","extreme weather","sea level rise","deforestation","carbon capture",
 "green hydrogen","nuclear energy","battery storage","climate policy","fossil fuels","net zero","biodiversity loss",
 "ocean warming"]
for t in CLIMATE: gnews_q("climate", t, t)
for s in ["climate","climatechange","environment","renewableenergy","energy","solar","electricvehicles",
          "sustainability","ClimateActionPlan","ClimateOffensive"]:
    reddit("climate", s)

# --- COMMODITIES --------------------------------------------------------------
COMM = ["gold price","silver price","crude oil price","natural gas","copper price","wheat corn prices",
 "coffee prices","lithium","rare earth metals","uranium price","OPEC oil","agricultural commodities",
 "palladium platinum","iron ore","cocoa prices"]
for t in COMM: gnews_q("commodities", t, t)

# --- DISASTERS ----------------------------------------------------------------
DIS = ["earthquake","hurricane","wildfire","flooding","tornado","volcano eruption","tsunami","drought",
 "landslide","typhoon","severe storm","heat wave","cyclone","natural disaster","evacuation emergency"]
for t in DIS: gnews_q("disasters", t, t)

# --- AVIATION -----------------------------------------------------------------
AV = ["airline industry","Boeing aircraft","Airbus","flight delays","aviation safety","air travel",
 "pilot shortage","airport expansion","jet engine","commercial aviation"]
for t in AV: gnews_q("aviation", t, t)

# ==== validate ===============================================================
def count_items(text:str)->int:
    try: root=ET.fromstring(text)
    except Exception: return 0
    ns={"atom":"http://www.w3.org/2005/Atom"}
    n=0
    if root.tag.endswith("feed"):
        for e in root.findall("atom:entry",ns):
            t=e.findtext("atom:title","",ns)
            if t and t.strip(): n+=1
    else:
        ch=root.find("channel")
        base= ch if ch is not None else root
        for it in base.findall("item"):
            t=it.findtext("title")
            if t and t.strip(): n+=1
    return n

async def check(client,cat,label,url,sem):
    async with sem:
        for attempt in range(2):
            try:
                r=await client.get(url)
                if r.status_code==200 and count_items(r.text)>=1:
                    return (cat,label,url,True)
                if r.status_code in (429,503) and attempt==0:
                    await asyncio.sleep(1.5); continue
                return (cat,label,url,False)
            except Exception:
                if attempt==0: await asyncio.sleep(0.8); continue
                return (cat,label,url,False)

async def main():
    seen=set(); uniq=[]
    for c,l,u in CAND:
        if u in seen: continue
        seen.add(u); uniq.append((c,l,u))
    print(f"expansion candidates: {len(uniq)}",file=sys.stderr)
    sem=asyncio.Semaphore(25)
    async with httpx.AsyncClient(timeout=12,follow_redirects=True,
                                 headers={"User-Agent":"pulse-agent/1.0"}) as client:
        res=await asyncio.gather(*[check(client,c,l,u,sem) for c,l,u in uniq])
    ok=[r for r in res if r[3]]
    print(f"expansion verified: {len(ok)}/{len(uniq)}",file=sys.stderr)
    # merge with existing
    existing=json.load(open("/root/pulse/verified_feeds.json"))
    have=set(u for lst in existing.values() for _,u in lst)
    added=0
    for c,l,u,_ in ok:
        if u in have: continue
        existing.setdefault(c,[]).append([l,u]); have.add(u); added+=1
    total=sum(len(v) for v in existing.values())
    json.dump(existing,open("/root/pulse/verified_feeds.json","w"),indent=1)
    print(f"added {added} new. TOTAL verified feeds: {total}",file=sys.stderr)
    print("by category:",{k:len(v) for k,v in sorted(existing.items())},file=sys.stderr)

asyncio.run(main())
