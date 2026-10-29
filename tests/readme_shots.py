"""Capture every README screenshot. Desktop only, 1440 x 900.

Usage:  python tests/readme_shots.py [base_url]
Needs:  pip install playwright && playwright install chromium

Two kinds of shot:
  * Live site pages, captured from the running deployment (default
    https://getpulsedata.online). The dashboard needs a signed-in session, so
    the browser stubs only the account endpoints (/auth/*). Every feed, seal
    and on-chain proof shown is real data from the live API.
  * Terminal shots. The script runs the real commands first (curl, verify.py,
    tests/tamper_demo.py, the MCP tool) and renders their actual output. Nothing
    in a terminal shot is typed by hand.
"""
import asyncio, html, json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BASE = sys.argv[1] if len(sys.argv) > 1 else "https://getpulsedata.online"
DAY = "2026-10-28"  # first anchored day
OUT = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)

AUTH_STUB = r"""(()=>{const of=window.fetch;window.fetch=async(u,o)=>{u=String(u);
if(u.includes('/auth/me'))return new Response(JSON.stringify({email:'demo@pulse.dev',name:'Demo'}),{status:200});
if(u.includes('/auth/keys'))return new Response(JSON.stringify({keys:[]}),{status:200});
if(u.includes('/auth/categories')){const c=await (await of('/data/categories')).json();
 for(const k in c)c[k].enabled=['crypto','regulatory','politics','news'].includes(k);
 return new Response(JSON.stringify(c),{status:200});}
return of(u,o);};})();"""


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    return (r.stdout or r.stderr).rstrip()


def curl_output():
    with urllib.request.urlopen(BASE + "/data/feed/regulatory", timeout=60) as r:
        d = json.load(r)
    d = d.get("data", d)
    arts = d["articles"]
    view = {"snapshot": {k: d["snapshot"][k] for k in ("fetched_at", "digest")},
            "articles": [{k: a[k] for k in ("feed", "title", "published", "url", "sha256")} for a in arts[:2]]}
    return json.dumps(view, indent=2, ensure_ascii=False) + f"\n... {len(arts)} articles in total"


def mcp_output():
    sys.path.insert(0, ROOT)
    import mcp_server
    out = asyncio.run(mcp_server.pulse_regulatory("SEC", 5))
    # Same lines the agent receives; only the long source links are cut for the picture.
    rows = []
    for l in out.split("\n"):
        parts = l.split(" | ")
        rows.append(" | ".join(p for p in parts if not p.startswith("http")))
    return "\n".join(rows) + "\n\n(source links cut from this picture, the agent gets them in full)"


def terminal_page(title, cmd, body):
    hl = html.escape(body)
    for word, cls in (("VERIFIED", "ok"), ("MISMATCH", "bad"), ("verified:     False", "bad"),
                      (" ok ", "ok"), ("NOT ok", "bad")):
        hl = hl.replace(word, f'<b class="{cls}">{word}</b>')
    return f"""<html><head><style>
@import url('https://fonts.googleapis.com/css2?family=Onest:wght@500;700&family=Space+Mono&display=swap');
body{{margin:0;background:#0d0c0b;font-family:Onest;display:flex;align-items:center;justify-content:center;height:100vh}}
.card{{width:1240px;background:#161513;border:1px solid #2a2826;border-radius:16px;overflow:hidden}}
.bar{{padding:16px 22px;border-bottom:1px solid #2a2826;color:#8a857e;font-size:15px;display:flex;gap:10px;align-items:center}}
.dot{{width:11px;height:11px;border-radius:50%;background:#2a2826}} .t{{margin-left:10px;color:#f0ede8;font-weight:700}}
pre{{margin:0;padding:24px 28px;color:#d8d4cd;font:15px/1.6 'Space Mono';white-space:pre-wrap;overflow-wrap:break-word;max-height:720px;overflow:hidden}}
.p{{color:#75e5b0}} .ok{{color:#75e5b0}} .bad{{color:#ff6b6b}}
</style></head><body><div class="card"><div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
<span class="t">{html.escape(title)}</span></div><pre><span class="p">$</span> {html.escape(cmd)}\n\n{hl}</pre></div></body></html>"""


def shot(page, name, **kw):
    page.screenshot(path=os.path.join(OUT, name), **kw)
    print("wrote", name)


def section(page, name, sel):
    # Scroll the section to the top of a normal viewport, so scroll animations
    # finish and the sticky nav sits where a visitor sees it.
    top = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + scrollY")
    h = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().height")
    page.evaluate(f"scrollTo(0, {top})"); time.sleep(2.5)
    page.set_viewport_size({"width": 1440, "height": int(min(max(h, 700), 1300))}); time.sleep(1.5)
    shot(page, name)
    page.set_viewport_size({"width": 1440, "height": 900})


terminals = [
    ("curl.png", "Ask the feed", f"curl {BASE}/data/feed/regulatory", curl_output()),
    ("verify.png", "Check a sealed day yourself", f"python3 verify.py {DAY}", run([sys.executable, "verify.py", DAY])),
    ("tamper.png", "Try to fake the record", f"python3 tests/tamper_demo.py {DAY}",
     run([sys.executable, "tests/tamper_demo.py", DAY])),
    ("mcp.png", "An AI agent calling Pulse (MCP tool)", 'pulse_regulatory(query="SEC", limit=5)', mcp_output()),
]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    pg = ctx.new_page()

    # Landing page, top to bottom
    pg.goto(BASE + "/", wait_until="networkidle"); time.sleep(2)
    shot(pg, "landing.png")
    section(pg, "landing-livedemo.png", "#livedemo")
    section(pg, "landing-categories.png", "#work")
    section(pg, "landing-how.png", "#process")

    # Dashboard (account endpoints stubbed, data is live)
    pg.add_init_script(AUTH_STUB)
    pg.goto(BASE + "/dashboard?feed=regulatory", wait_until="networkidle")
    pg.wait_for_selector(".pv-seal", timeout=60000); time.sleep(1.5)
    shot(pg, "dashboard-overview.png")
    pg.query_selector(".preview-content").scroll_into_view_if_needed(); time.sleep(.6)
    shot(pg, "regulatory-feed.png")
    box = pg.query_selector(".preview-content").bounding_box()
    shot(pg, "seal.png", clip={"x": box["x"] - 24, "y": box["y"] - 24, "width": box["width"] + 48, "height": min(box["height"], 470) + 24})
    for sec in ("feeds", "docs"):
        pg.evaluate(f"showSection('{sec}')"); pg.evaluate("scrollTo(0,0)"); time.sleep(2)
        h = pg.evaluate(f"document.getElementById('sec-{sec}').getBoundingClientRect().bottom") + 40
        pg.set_viewport_size({"width": 1440, "height": int(min(max(h, 900), 1500))}); time.sleep(1)
        shot(pg, f"dashboard-{sec}.png")
        pg.set_viewport_size({"width": 1440, "height": 900})

    # Raw API: the day's sealed snapshot
    pg.goto(f"{BASE}/data/regulatory/snapshot/{DAY}", wait_until="networkidle"); time.sleep(1)
    snap = pg.evaluate("document.body.innerText")
    d = json.loads(snap)
    first = {k: d["items"][0][k] for k in ("feed", "title", "published", "sha256")}
    d["items"] = [first, f"... and {len(d['items']) - 1} more sealed items"]
    terminals.insert(1, ("snapshot.png", "The sealed record for one day",
                         f"curl {BASE}/data/regulatory/snapshot/{DAY}",
                         json.dumps(d, indent=2, ensure_ascii=False)))

    # The anchor on the public block explorer (not Pulse)
    # The explorer renders blank for headless user agents, so use a normal one.
    tx = json.loads(snap)["onchain"]["explorer"]
    ex = b.new_context(viewport={"width": 1440, "height": 900}, user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"))
    ep = ex.new_page()
    ep.goto(tx, wait_until="domcontentloaded", timeout=60000)
    ep.wait_for_function("document.body.innerText.includes('PULSE-REG:v1')", timeout=60000); time.sleep(2)
    ep.get_by_text("View More", exact=True).first.click(); time.sleep(2)
    found = ep.evaluate("""(()=>{const all=[...document.querySelectorAll('body *')].filter(e=>e.textContent.includes('PULSE-REG:v1'));
      const w=all[all.length-1]; if(!w) return false;
      w.style.outline='3px solid #75e5b0'; w.style.outlineOffset='6px'; w.scrollIntoView({block:'center'}); return true;})()""")
    print("explorer highlight", found); time.sleep(1.5)
    shot(ep, "explorer.png")
    ex.close()

    # Terminal shots from real command output
    for name, title, cmd, body in terminals:
        pg.set_content(terminal_page(title, cmd, body)); time.sleep(1.2)
        shot(pg, name)
    b.close()
