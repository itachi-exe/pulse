#!/usr/bin/env python3
"""Build a large candidate RSS catalog and validate every feed against the
EXACT runtime parse contract used by auth_service._fetch_rss (stdlib ET).
Only feeds that return >=1 real item with a title are kept.
Writes verified_feeds.py (a python list) + prints stats.
"""
import asyncio, xml.etree.ElementTree as ET, httpx, json, sys

# ---- candidate families -----------------------------------------------------
CANDIDATES = {}  # category -> list[(label, url)]

def add(cat, label, url):
    CANDIDATES.setdefault(cat, []).append((label, url))

# arXiv: ~150 real subject-class RSS feeds (export.arxiv.org/rss/<class>)
ARXIV = ["cs.AI","cs.CL","cs.CV","cs.LG","cs.NE","cs.RO","cs.CR","cs.DC","cs.DS","cs.SE",
 "cs.PL","cs.DB","cs.IR","cs.SY","cs.HC","cs.CY","cs.GT","cs.CG","cs.CC","cs.AR",
 "cs.OS","cs.NI","cs.MA","cs.MM","cs.GL","cs.LO","cs.MS","cs.NA","cs.SC","cs.SD",
 "math.AG","math.AT","math.AP","math.CT","math.CA","math.CO","math.AC","math.CV","math.DG","math.DS",
 "math.FA","math.GM","math.GN","math.GT","math.GR","math.HO","math.IT","math.KT","math.LO","math.MP",
 "math.MG","math.NT","math.NA","math.OA","math.OC","math.PR","math.QA","math.RT","math.RA","math.SP",
 "math.ST","math.SG","physics.acc-ph","physics.ao-ph","physics.app-ph","physics.atom-ph","physics.bio-ph",
 "physics.chem-ph","physics.class-ph","physics.comp-ph","physics.data-an","physics.flu-dyn","physics.gen-ph",
 "physics.geo-ph","physics.hist-ph","physics.ins-det","physics.med-ph","physics.optics","physics.plasm-ph",
 "physics.pop-ph","physics.soc-ph","physics.space-ph","astro-ph.CO","astro-ph.EP","astro-ph.GA",
 "astro-ph.HE","astro-ph.IM","astro-ph.SR","cond-mat.dis-nn","cond-mat.mes-hall","cond-mat.mtrl-sci",
 "cond-mat.other","cond-mat.quant-gas","cond-mat.soft","cond-mat.stat-mech","cond-mat.str-el","cond-mat.supr-con",
 "q-bio.BM","q-bio.CB","q-bio.GN","q-bio.MN","q-bio.NC","q-bio.OT","q-bio.PE","q-bio.QM","q-bio.SC","q-bio.TO",
 "q-fin.CP","q-fin.EC","q-fin.GN","q-fin.MF","q-fin.PM","q-fin.PR","q-fin.RM","q-fin.ST","q-fin.TR",
 "stat.AP","stat.CO","stat.ME","stat.ML","stat.OT","stat.TH","eess.AS","eess.IV","eess.SP","eess.SY",
 "hep-ex","hep-lat","hep-ph","hep-th","gr-qc","nucl-ex","nucl-th","quant-ph","nlin.AO","nlin.CG",
 "nlin.CD","nlin.PS","nlin.SI","econ.EM","econ.GN","econ.TH"]
for c in ARXIV:
    add("science", f"arXiv {c}", f"http://export.arxiv.org/rss/{c}")

# NYT sections (rss.nytimes.com/services/xml/rss/nyt/<sec>.xml)
NYT = ["HomePage","World","Africa","Americas","AsiaPacific","Europe","MiddleEast","US","Politics",
 "Upshot","NYRegion","Business","EnergyEnvironment","SmallBusiness","Economy","DealBook","MediaandAdvertising",
 "YourMoney","Technology","PersonalTech","Science","Climate","Space","Health","Well","Sports","Baseball",
 "CollegeBasketball","CollegeFootball","Golf","Hockey","ProBasketball","ProFootball","Soccer","Tennis",
 "Arts","ArtandDesign","Books","Dance","Movies","Music","Television","Theater","Travel","Jobs","RealEstate","Automobiles"]
NYT_CAT = {"World":"news","Politics":"politics","Business":"finance","Economy":"finance","DealBook":"finance",
 "Technology":"tech","PersonalTech":"tech","Science":"science","Climate":"climate","Space":"space",
 "Health":"medical","Well":"medical","Sports":"sports"}
for s in NYT:
    add(NYT_CAT.get(s,"news"), f"NYT {s}", f"https://rss.nytimes.com/services/xml/rss/nyt/{s}.xml")

# Guardian sections (theguardian.com/<sec>/rss)
GUARDIAN = [("world","news"),("politics","politics"),("us-news","news"),("uk-news","news"),
 ("business","finance"),("technology","tech"),("science","science"),("environment","climate"),
 ("sport","sports"),("football","sports"),("global-development","news"),("world/coronavirus-outbreak","medical"),
 ("society/health","medical"),("money","finance"),("games","gaming"),("artanddesign","news"),
 ("books","news"),("film","news"),("music","news"),("media","tech"),("law","politics"),
 ("education","news"),("cities","news"),("inequality","news"),("global/energy","climate")]
for sec,cat in GUARDIAN:
    add(cat, f"Guardian {sec}", f"https://www.theguardian.com/{sec}/rss")

# BBC sections
BBC = [("news/world","news"),("news/politics","politics"),("news/business","finance"),
 ("news/technology","tech"),("news/science_and_environment","science"),("news/health","medical"),
 ("sport","sports"),("news/world/africa","news"),("news/world/asia","news"),("news/world/europe","news"),
 ("news/world/us_and_canada","news"),("news/world/latin_america","news"),("news/world/middle_east","news"),
 ("news/education","news"),("news/entertainment_and_arts","news")]
for sec,cat in BBC:
    add(cat, f"BBC {sec}", f"https://feeds.bbci.co.uk/{sec}/rss.xml")

# Stack Exchange network (~180 sites) feeds.  https://<site>.stackexchange.com/feeds
SE_SITES = ["stackoverflow","serverfault","superuser","askubuntu","math","stats","physics","chemistry",
 "biology","cs","cstheory","datascience","ai","softwareengineering","codereview","security","crypto",
 "dba","devops","networkengineering","unix","apple","android","gaming","webmasters","webapps","wordpress",
 "magento","drupal","sharepoint","salesforce","gis","ux","graphicdesign","dsp","electronics","robotics",
 "arduino","raspberrypi","reverseengineering","law","politics","economics","money","academia","workplace",
 "history","philosophy","english","linguistics","writing","worldbuilding","scifi","movies","music","sound",
 "photo","cooking","health","fitness","bicycles","outdoors","travel","gardening","diy","homeimprovement",
 "mechanics","aviation","space","astronomy","earthscience","quant","bitcoin","ethereum","tor","opendata",
 "sports","boardgames","rpg","puzzling","chess","poker","mathoverflow","tex","emacs","vi","unix",
 "mathematica","or","scicomp","codegolf","retrocomputing","hardwarerecs","softwarerecs","3dprinting",
 "iot","expressionengine","craftcms","wordpress","ebooks","freelancing","pm","productivity","sustainability",
 "eosio","stellar","monero","hsm","cardano","solana","conlang","latin","german","spanish","french",
 "russian","japanese","chinese","korean","italian","portuguese","esperanto","ukrainian","hinduism",
 "islam","judaism","christianity","buddhism","skeptics","parenting","pets","interpersonal","hermeneutics",
 "psychology","cogsci","medicalsciences","biology","genetics","matheducation","tridion","alcohol",
 "coffee","beer","homebrew","martialarts","hsm","materials","engineering","electronics","controls"]
SE_CAT = {"ai":"tech","datascience":"tech","cs":"tech","security":"cybersecurity","crypto":"cybersecurity",
 "bitcoin":"crypto","ethereum":"crypto","monero":"crypto","cardano":"crypto","stellar":"crypto",
 "politics":"politics","economics":"finance","money":"finance","quant":"finance","space":"space",
 "astronomy":"space","health":"medical","medicalsciences":"medical","fitness":"medical","sports":"sports",
 "gaming":"gaming","boardgames":"gaming","rpg":"gaming","chess":"gaming","poker":"gaming"}
seen_se=set()
for s in SE_SITES:
    if s in seen_se: continue
    seen_se.add(s)
    dom = "stackoverflow.com" if s=="stackoverflow" else (
          "serverfault.com" if s=="serverfault" else
          "superuser.com" if s=="superuser" else
          "askubuntu.com" if s=="askubuntu" else
          "mathoverflow.net" if s=="mathoverflow" else f"{s}.stackexchange.com")
    add(SE_CAT.get(s,"tech"), f"StackExchange {s}", f"https://{dom}/feeds")

# Google News topic + search RSS (news.google.com/rss) — many distinct topics
GNEWS = [("WORLD","news"),("NATION","news"),("BUSINESS","finance"),("TECHNOLOGY","tech"),
 ("ENTERTAINMENT","news"),("SPORTS","sports"),("SCIENCE","science"),("HEALTH","medical")]
for t,cat in GNEWS:
    add(cat, f"Google News {t}", f"https://news.google.com/rss/headlines/section/topic/{t}?hl=en-US&gl=US&ceid=US:en")
GNEWS_Q = ["artificial intelligence","cybersecurity","climate change","stock market","cryptocurrency",
 "elections","public health","space exploration","semiconductors","electric vehicles","inflation",
 "renewable energy","biotechnology","quantum computing","supply chain","interest rates","oil prices",
 "vaccine","earthquake","hurricane","wildfire","data breach","merger acquisition","IPO","layoffs"]
GQ_CAT = {"stock market":"finance","cryptocurrency":"crypto","inflation":"finance","interest rates":"finance",
 "oil prices":"commodities","public health":"medical","vaccine":"medical","earthquake":"disasters",
 "hurricane":"disasters","wildfire":"disasters","cybersecurity":"cybersecurity","data breach":"cybersecurity",
 "space exploration":"space","climate change":"climate","renewable energy":"climate","elections":"politics"}
for q in GNEWS_Q:
    add(GQ_CAT.get(q,"news"), f"GNews: {q}", f"https://news.google.com/rss/search?q={q.replace(' ','%20')}&hl=en-US&gl=US&ceid=US:en")

# Reddit — many subreddit .rss feeds
REDDIT = [("worldnews","news"),("news","news"),("politics","politics"),("technology","tech"),
 ("science","science"),("space","space"),("Health","medical"),("medicine","medical"),
 ("cybersecurity","cybersecurity"),("netsec","cybersecurity"),("CryptoCurrency","crypto"),
 ("Bitcoin","crypto"),("ethereum","crypto"),("investing","finance"),("stocks","finance"),
 ("economics","finance"),("wallstreetbets","finance"),("gaming","gaming"),("Games","gaming"),
 ("sports","sports"),("soccer","sports"),("nba","sports"),("worldpolitics","politics"),
 ("EnergyNews","climate"),("climate","climate"),("askscience","science"),("Futurology","tech"),
 ("MachineLearning","tech"),("artificial","tech"),("programming","tech"),("dataisbeautiful","tech")]
for sub,cat in REDDIT:
    add(cat, f"r/{sub}", f"https://www.reddit.com/r/{sub}/.rss")

# Nature journals (nature.com/<jrnl>.rss)
NATURE = ["nature","nbt","nmeth","ngeo","nphys","nchem","nmat","nnano","nphoton","ncomms","natmachintell",
 "nrg","ni","nm","nrd","nrc","nrmicro","nrn","nrneurol","nrcardio","nrclinonc","srep","nplants","natecolevol",
 "natastron","nataging","natfood","natwater","natcancer","natcardiovascres","natmetab","natrevmats"]
for j in NATURE:
    add("science", f"Nature {j}", f"https://www.nature.com/{j}.rss")

# US government / agency feeds
GOV = [("USGS Quakes M2.5", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.atom","disasters"),
 ("USGS Quakes M4.5","https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.atom","disasters"),
 ("NWS Alerts US","https://alerts.weather.gov/cap/us.php?x=0","disasters"),
 ("CISA Advisories","https://www.cisa.gov/cybersecurity-advisories/all.xml","cybersecurity"),
 ("FDA Recalls","https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/food-safety/rss.xml","medical"),
 ("CDC Newsroom","https://tools.cdc.gov/api/v2/resources/media/403372.rss","medical"),
 ("NASA Breaking","https://www.nasa.gov/rss/dyn/breaking_news.rss","space"),
 ("NASA Image of Day","https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss","space"),
 ("SEC Press","https://www.sec.gov/news/pressreleases.rss","finance"),
 ("Federal Reserve","https://www.federalreserve.gov/feeds/press_all.xml","finance"),
 ("Treasury","https://home.treasury.gov/rss/press.xml","finance"),
 ("BLS News","https://www.bls.gov/feed/news_release/rss.xml","finance"),
 ("EPA News","https://www.epa.gov/newsreleases/search/rss","climate"),
 ("NOAA","https://www.noaa.gov/media-releases.xml","climate"),
 ("NIH News","https://www.nih.gov/news-events/news-releases/feed","medical"),
 ("State Dept","https://www.state.gov/rss-feed/press-releases/feed/","politics"),
 ("White House","https://www.whitehouse.gov/feed/","politics"),
 ("EU Commission","https://ec.europa.eu/commission/presscorner/api/rss?language=en","politics"),
 ("UN News","https://news.un.org/feed/subscribe/en/news/all/rss.xml","news"),
 ("WHO News","https://www.who.int/rss-feeds/news-english.xml","medical")]
for label,url,cat in GOV:
    add(cat, label, url)

# Major outlets / verticals (distinct feeds)
OUTLETS = [
 ("Reuters World","https://www.reutersagency.com/feed/?best-topics=world&post_type=best","news"),
 ("AP Top","https://feeds.apnews.com/rss/apf-topnews","news"),
 ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml","news"),
 ("NPR News","https://feeds.npr.org/1001/rss.xml","news"),
 ("CNBC Top","https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114","finance"),
 ("CNBC Finance","https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664","finance"),
 ("MarketWatch","https://feeds.content.dowjones.io/public/rss/mw_topstories","finance"),
 ("Yahoo Finance","https://finance.yahoo.com/news/rssindex","finance"),
 ("Investing.com","https://www.investing.com/rss/news.rss","finance"),
 ("CoinDesk","https://www.coindesk.com/arc/outboundfeeds/rss/","crypto"),
 ("Cointelegraph","https://cointelegraph.com/rss","crypto"),
 ("Decrypt","https://decrypt.co/feed","crypto"),
 ("Bitcoin Magazine","https://bitcoinmagazine.com/.rss/full/","crypto"),
 ("The Block","https://www.theblock.co/rss.xml","crypto"),
 ("TechCrunch","https://techcrunch.com/feed/","tech"),
 ("The Verge","https://www.theverge.com/rss/index.xml","tech"),
 ("Wired","https://www.wired.com/feed/rss","tech"),
 ("Ars Technica","https://feeds.arstechnica.com/arstechnica/index","tech"),
 ("Engadget","https://www.engadget.com/rss.xml","tech"),
 ("MIT Tech Review","https://www.technologyreview.com/feed/","tech"),
 ("VentureBeat","https://venturebeat.com/feed/","tech"),
 ("Hacker News","https://news.ycombinator.com/rss","tech"),
 ("The Hacker News","https://feeds.feedburner.com/TheHackersNews","cybersecurity"),
 ("BleepingComputer","https://www.bleepingcomputer.com/feed/","cybersecurity"),
 ("Krebs on Security","https://krebsonsecurity.com/feed/","cybersecurity"),
 ("Dark Reading","https://www.darkreading.com/rss.xml","cybersecurity"),
 ("Threatpost","https://threatpost.com/feed/","cybersecurity"),
 ("SecurityWeek","https://feeds.feedburner.com/securityweek","cybersecurity"),
 ("ESPN Top","https://www.espn.com/espn/rss/news","sports"),
 ("Sky Sports","https://www.skysports.com/rss/12040","sports"),
 ("BBC Sport","https://feeds.bbci.co.uk/sport/rss.xml","sports"),
 ("Polygon","https://www.polygon.com/rss/index.xml","gaming"),
 ("Eurogamer","https://www.eurogamer.net/feed","gaming"),
 ("IGN","https://feeds.ign.com/ign/all","gaming"),
 ("Kotaku","https://kotaku.com/rss","gaming"),
 ("PC Gamer","https://www.pcgamer.com/rss/","gaming"),
 ("Rock Paper Shotgun","https://www.rockpapershotgun.com/feed","gaming"),
 ("Space.com","https://www.space.com/feeds/all","space"),
 ("Universe Today","https://www.universetoday.com/feed/","space"),
 ("Phys.org","https://phys.org/rss-feed/","science"),
 ("ScienceDaily","https://www.sciencedaily.com/rss/all.xml","science"),
 ("New Scientist","https://www.newscientist.com/feed/home/","science"),
 ("Scientific American","https://www.scientificamerican.com/platform/syndication/rss/","science"),
 ("Live Science","https://www.livescience.com/feeds/all","science"),
 ("STAT News","https://www.statnews.com/feed/","medical"),
 ("MedicalXpress","https://medicalxpress.com/rss-feed/","medical"),
 ("Kaiser Health","https://kffhealthnews.org/feed/","medical"),
 ("Politico","https://rss.politico.com/politics-news.xml","politics"),
 ("The Hill","https://thehill.com/rss/syndicator/19110","politics"),
 ("Axios","https://api.axios.com/feed/","news"),
 ("Deutsche Welle","https://rss.dw.com/xml/rss-en-all","news"),
 ("France 24","https://www.france24.com/en/rss","news"),
 ("SCMP","https://www.scmp.com/rss/91/feed","news"),
 ("Times of India","https://timesofindia.indiatimes.com/rssfeeds/296589292.cms","news"),
 ("The Economist","https://www.economist.com/finance-and-economics/rss.xml","finance"),
 ("FT Companies","https://www.ft.com/companies?format=rss","finance"),
 ("Bloomberg Markets","https://feeds.bloomberg.com/markets/news.rss","finance"),
 ("Climate Home","https://www.climatechangenews.com/feed/","climate"),
 ("Carbon Brief","https://www.carbonbrief.org/feed/","climate"),
 ("Inside Climate","https://insideclimatenews.org/feed/","climate"),
 ("Grist","https://grist.org/feed/","climate"),
 ("OilPrice","https://oilprice.com/rss/main","commodities"),
 ("Mining.com","https://www.mining.com/feed/","commodities"),
 ("Kitco News","https://www.kitco.com/rss/KitcoNews.xml","commodities"),
 ("AgWeb","https://www.agweb.com/rss.xml","commodities"),
 ("FlightGlobal","https://www.flightglobal.com/rss/","aviation"),
 ("Aviation Week","https://aviationweek.com/rss.xml","aviation"),
 ("Simple Flying","https://simpleflying.com/feed/","aviation"),
 ("AVweb","https://www.avweb.com/feed/","aviation"),
]
for label,url,cat in OUTLETS:
    add(cat, label, url)

# ---- validation -------------------------------------------------------------
def parse_ok(text: str) -> int:
    """Replicates auth_service._fetch_rss: parse with ET, count items w/ titles."""
    try:
        root = ET.fromstring(text)
    except Exception:
        return 0
    ns = {"atom":"http://www.w3.org/2005/Atom"}
    n = 0
    if root.tag.endswith("feed"):
        for e in root.findall("atom:entry", ns):
            t = e.findtext("atom:title", "", ns)
            if t and t.strip(): n += 1
    else:
        ch = root.find("channel")
        for it in (ch or root).findall("item"):
            t = it.findtext("title")
            if t and t.strip(): n += 1
    return n

async def check(client, cat, label, url, sem):
    async with sem:
        try:
            r = await client.get(url)
            if r.status_code != 200:
                return (cat, label, url, False, f"http {r.status_code}")
            n = parse_ok(r.text)
            return (cat, label, url, n >= 1, f"{n} items")
        except Exception as e:
            return (cat, label, url, False, type(e).__name__)

async def main():
    all_feeds = [(cat,label,url) for cat,lst in CANDIDATES.items() for label,url in lst]
    # dedupe by url
    seen=set(); uniq=[]
    for cat,label,url in all_feeds:
        if url in seen: continue
        seen.add(url); uniq.append((cat,label,url))
    print(f"candidates: {len(uniq)} unique urls across {len(CANDIDATES)} categories", file=sys.stderr)
    sem = asyncio.Semaphore(40)
    async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                 headers={"User-Agent":"pulse-agent/1.0"}) as client:
        results = await asyncio.gather(*[check(client,c,l,u,sem) for c,l,u in uniq])
    ok = [r for r in results if r[3]]
    bad = [r for r in results if not r[3]]
    from collections import Counter
    bycat = Counter(r[0] for r in ok)
    print(f"VERIFIED: {len(ok)} / {len(uniq)}", file=sys.stderr)
    print(f"by category: {dict(bycat)}", file=sys.stderr)
    # write verified feeds grouped by category
    out = {}
    for cat,label,url,_,_ in ok:
        out.setdefault(cat, []).append([label,url])
    with open("/root/pulse/verified_feeds.json","w") as f:
        json.dump(out, f, indent=1)
    with open("/root/pulse/failed_feeds.json","w") as f:
        json.dump([[c,l,u,m] for c,l,u,_,m in bad], f, indent=1)
    print(f"wrote verified_feeds.json ({len(ok)} feeds)", file=sys.stderr)

asyncio.run(main())
