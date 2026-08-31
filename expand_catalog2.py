#!/usr/bin/env python3
"""Third pass: push over 1000 with more REAL live feeds (Google News search per
distinct query + Stack Exchange tag feeds). Validate + merge. Verified only.
"""
import asyncio, xml.etree.ElementTree as ET, httpx, json, sys

CAND=[]
def gq(cat,q): CAND.append((cat,f"GNews: {q}",f"https://news.google.com/rss/search?q={q.replace(' ','%20').replace('&','%26')}&hl=en-US&gl=US&ceid=US:en"))
def gq_region(cat,q,gl,ceid,lang="en"): CAND.append((cat,f"GNews[{gl}]: {q}",f"https://news.google.com/rss/search?q={q.replace(' ','%20')}&hl={lang}&gl={gl}&ceid={ceid}"))
def se(cat,site,tag):
    dom={"stackoverflow":"stackoverflow.com","serverfault":"serverfault.com","superuser":"superuser.com","mathoverflow":"mathoverflow.net"}.get(site,f"{site}.stackexchange.com")
    CAND.append((cat,f"SE {site}/{tag}",f"https://{dom}/feeds/tag/{tag.replace('#','%23').replace('+','%2b')}"))

# More finance: sectors, ETFs, forex pairs, indices worldwide
for q in ["FTSE 100","DAX index","Nikkei 225","Hang Seng","CAC 40","Sensex","ASX 200","TSX index",
 "KOSPI","Shanghai Composite","VIX volatility","gold ETF","Treasury bonds","junk bonds","municipal bonds",
 "EUR USD","GBP USD","USD JPY","USD CNY","Swiss franc","emerging market debt","REIT","utility stocks",
 "energy stocks","bank stocks","semiconductor stocks","biotech stocks","airline stocks","retail stocks",
 "defense stocks","auto stocks","insurance stocks","pharma stocks","consumer staples","industrial stocks",
 "materials sector","real estate stocks","small cap stocks","value stocks","growth stocks","momentum stocks",
 "quarterly earnings","analyst ratings","stock split","insider trading","activist investor","credit rating",
 "corporate debt","sovereign debt","yield curve","quantitative tightening","money supply","retail sales data",
 "manufacturing PMI","services PMI","consumer confidence","durable goods orders","trade deficit","budget deficit"]:
    gq("finance",q)

# More tech: frameworks, companies, niche
for q in ["React framework","Vue.js","Angular","Next.js","Svelte","Django","Flask","FastAPI","Spring Boot",
 ".NET","Node.js","Deno","Bun runtime","WebAssembly","GraphQL","PostgreSQL","MongoDB","Redis","Elasticsearch",
 "Apache Kafka","Docker containers","Terraform","Ansible","GitHub Copilot","GitLab","Jenkins CI","observability",
 "vector database","RAG retrieval","AI agents","multimodal AI","fine-tuning LLM","prompt engineering",
 "AI chips","neuromorphic computing","photonic computing","6G research","brain computer interface","humanoid robots",
 "drone technology","3D printing","smart glasses","foldable phones","wearable technology","digital twin",
 "blockchain enterprise","zero knowledge proofs","homomorphic encryption","post quantum cryptography",
 "self driving Waymo","Tesla FSD","lidar sensors","battery recycling","solid state battery","chip export controls"]:
    gq("tech",q)

# More medical
for q in ["RSV virus","dengue fever","cholera outbreak","polio","hepatitis","sepsis","antimicrobial resistance",
 "rare disease","organ transplant","stem cell therapy","immunotherapy","mRNA vaccine","GLP-1 drugs","weight loss surgery",
 "Parkinson's disease","multiple sclerosis","autism research","ADHD","depression treatment","anxiety disorder",
 "chronic pain","arthritis","kidney disease","liver disease","lung cancer","breast cancer","prostate cancer",
 "colon cancer","leukemia","pediatric health","geriatric care","womens health","reproductive health",
 "nutrition science","gut microbiome","sleep medicine","vaccine hesitancy","health insurance policy","Medicare",
 "hospital staffing","nursing shortage","medical AI diagnostics","wearable health monitor"]:
    gq("medical",q)

# More politics/world regional
for q in ["Taiwan China tension","South China Sea","Korea peninsula","Afghanistan Taliban","Syria conflict",
 "Yemen war","Sudan conflict","Ethiopia Tigray","Congo conflict","Sahel security","Venezuela crisis",
 "Haiti crisis","Cuba US relations","Balkans","Caucasus Armenia Azerbaijan","Kashmir","Myanmar coup",
 "Hong Kong","Belarus","Poland politics","Hungary EU","Italy government","Spain politics","Scotland independence",
 "Catalonia","Quebec","Mexico cartels","Central America migration","BRICS expansion","African Union summit",
 "ASEAN summit","Arab League","OPEC politics","UN Security Council","International Criminal Court","war crimes tribunal",
 "nuclear arms control","cyber warfare policy","election interference","disinformation campaign","press freedom"]:
    gq("politics",q)

# More cybersecurity CVE/vendors
for q in ["Microsoft patch Tuesday","Windows vulnerability","Linux kernel security","Android security patch",
 "iOS security","Cisco vulnerability","Fortinet VPN","Palo Alto firewall","VMware exploit","Citrix bleed",
 "MOVEit breach","Okta breach","LastPass breach","SolarWinds","Log4j","ransomware gang LockBit","BlackCat ransomware",
 "Clop ransomware","North Korea Lazarus","Chinese APT","Russian hackers","Iranian hackers","credential stuffing",
 "business email compromise","SIM swapping","deepfake fraud","AI phishing","cloud misconfiguration","Kubernetes security",
 "container security","API security","OAuth vulnerability","supply chain npm","PyPI malware","open source vulnerability"]:
    gq("cybersecurity",q)

# More science subjects
for q in ["dark matter","gravitational waves","quantum entanglement","superconductor room temperature","nuclear fusion breakthrough",
 "CRISPR gene editing","synthetic biology","protein folding AlphaFold","microbiome research","coral reef","Antarctic ice",
 "Arctic melting","asteroid mining","dinosaur discovery","human origins","ancient DNA","dark energy","neutrino",
 "quantum sensor","metamaterials","graphene","perovskite solar","wildlife conservation","insect decline","ocean acidification"]:
    gq("science",q)

# More space missions
for q in ["Artemis 2","Starship test","lunar Gateway","Mars sample return","Europa Clipper","Dragonfly Titan",
 "Chang'e Moon","Chandrayaan","Vera Rubin observatory","Roman telescope","exoplanet atmosphere","habitable zone",
 "space weather forecast","geomagnetic storm","Kessler syndrome","asteroid deflection DART","commercial space station",
 "space mining","reusable rockets","hypersonic","satellite internet","GPS Galileo","space force","Moon base"]:
    gq("space",q)

# More climate/energy
for q in ["carbon capture storage","direct air capture","green hydrogen production","offshore wind","floating solar",
 "geothermal energy","tidal energy","grid storage","EV charging network","heat pump","building electrification",
 "methane emissions","permafrost thaw","glacier retreat","coral bleaching","wildfire season","atmospheric river",
 "El Nino La Nina","carbon pricing","emissions trading","climate lawsuit","fossil fuel divestment","nuclear SMR",
 "lithium mining","cobalt supply","solar manufacturing"]:
    gq("climate",q)

# More sports leagues/teams
for q in ["Real Madrid","Barcelona","Manchester United","Manchester City","Liverpool FC","Arsenal FC","Chelsea FC",
 "Bayern Munich","Paris Saint-Germain","Juventus","Lakers","Warriors","Celtics","Cowboys","Patriots","Chiefs",
 "Yankees","Dodgers","Formula 1 Verstappen","Lewis Hamilton","Novak Djokovic","Carlos Alcaraz","LeBron James",
 "Lionel Messi","Cristiano Ronaldo","Super Bowl","NBA Finals","World Series","Stanley Cup","Wimbledon","US Open tennis"]:
    gq("sports",q)

# More gaming titles/platforms
for q in ["GTA 6 Rockstar","Call of Duty 2025","EA Sports FC","Fortnite","Valorant","League of Legends","Counter-Strike 2",
 "Elden Ring DLC","Baldur's Gate 3","Cyberpunk 2077","Starfield","Zelda","Mario","Pokemon game","Diablo 4",
 "World of Warcraft","Final Fantasy","PlayStation 6","Xbox Game Pass","Steam Deck","Nintendo Switch 2","Epic Games Store",
 "game studio acquisition","Microsoft Activision","esports tournament","Twitch streaming"]:
    gq("gaming",q)

# More commodities
for q in ["gold futures","silver futures","WTI crude","Brent crude","natural gas futures","copper futures",
 "aluminum price","nickel price","zinc price","tin price","wheat futures","corn futures","soybean futures",
 "sugar price","cotton price","cocoa futures","coffee futures","orange juice futures","cattle futures","lumber price",
 "lithium carbonate","cobalt price","graphite","uranium spot","platinum futures","palladium price","iron ore price"]:
    gq("commodities",q)

# More disasters/regional
for q in ["California wildfire","Japan earthquake","Turkey earthquake","Philippines typhoon","India flooding",
 "Australia bushfire","Atlantic hurricane","Pacific typhoon","Indonesia volcano","Iceland volcano","Italy earthquake",
 "Nepal earthquake","Chile earthquake","Mexico earthquake","US tornado","Europe heatwave","African drought",
 "Bangladesh cyclone","landslide disaster","dam failure"]:
    gq("disasters",q)

# More aviation
for q in ["Boeing 737 MAX","Boeing 787","Airbus A320","Airbus A350","aircraft order","airline earnings",
 "flight cancellation","FAA regulation","EASA","air traffic control","jet fuel price","airport security",
 "supersonic jet","electric aircraft","eVTOL air taxi","drone delivery","space tourism flight","cargo airline",
 "low cost carrier","airline merger"]:
    gq("aviation",q)

# More news regions (city-level)
for q in ["London news","Paris news","Tokyo news","New York news","Los Angeles news","Berlin news","Dubai news",
 "Singapore news","Hong Kong news","Mumbai news","Shanghai news","Sao Paulo news","Lagos news","Cairo news",
 "Istanbul news","Moscow news","Toronto news","Sydney news","Mexico City news","Jakarta news","Seoul news",
 "Bangkok news","Nairobi news","Johannesburg news","Buenos Aires news"]:
    gq("news",q)

# SE tags across popular sites for tech depth
for tag in ["machine-learning","deep-learning","neural-networks","nlp","reinforcement-learning","computer-vision"]:
    se("tech","datascience",tag); se("tech","ai",tag)
for tag in ["encryption","authentication","network","malware","penetration-test","tls","hashing","vpn"]:
    se("cybersecurity","security",tag)
for tag in ["bitcoin","ethereum","smart-contracts","wallet","mining","transactions"]:
    se("crypto","bitcoin",tag); se("crypto","ethereum",tag)

# ==== validate + merge =======================================================
def count_items(text):
    try: root=ET.fromstring(text)
    except Exception: return 0
    ns={"atom":"http://www.w3.org/2005/Atom"}; n=0
    if root.tag.endswith("feed"):
        for e in root.findall("atom:entry",ns):
            t=e.findtext("atom:title","",ns)
            if t and t.strip(): n+=1
    else:
        ch=root.find("channel"); base=ch if ch is not None else root
        for it in base.findall("item"):
            t=it.findtext("title")
            if t and t.strip(): n+=1
    return n

async def check(client,cat,label,url,sem):
    async with sem:
        for a in range(2):
            try:
                r=await client.get(url)
                if r.status_code==200 and count_items(r.text)>=1: return (cat,label,url,True)
                if r.status_code in (429,503) and a==0: await asyncio.sleep(1.5); continue
                return (cat,label,url,False)
            except Exception:
                if a==0: await asyncio.sleep(0.8); continue
                return (cat,label,url,False)

async def main():
    seen=set(); uniq=[]
    for c,l,u in CAND:
        if u in seen: continue
        seen.add(u); uniq.append((c,l,u))
    print(f"pass3 candidates: {len(uniq)}",file=sys.stderr)
    sem=asyncio.Semaphore(20)
    async with httpx.AsyncClient(timeout=12,follow_redirects=True,headers={"User-Agent":"pulse-agent/1.0"}) as client:
        res=await asyncio.gather(*[check(client,c,l,u,sem) for c,l,u in uniq])
    ok=[r for r in res if r[3]]
    print(f"pass3 verified: {len(ok)}/{len(uniq)}",file=sys.stderr)
    existing=json.load(open("/root/pulse/verified_feeds.json"))
    have=set(u for lst in existing.values() for _,u in lst); added=0
    for c,l,u,_ in ok:
        if u in have: continue
        existing.setdefault(c,[]).append([l,u]); have.add(u); added+=1
    total=sum(len(v) for v in existing.values())
    json.dump(existing,open("/root/pulse/verified_feeds.json","w"),indent=1)
    print(f"added {added}. TOTAL: {total}",file=sys.stderr)
    print("by category:",{k:len(v) for k,v in sorted(existing.items())},file=sys.stderr)

asyncio.run(main())
