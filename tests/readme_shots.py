"""Capture README screenshots from the live Pulse deployment.

Usage:  python tests/readme_shots.py [base_url]
Writes PNGs into docs/screenshots/. Needs: pip install playwright && playwright install chromium

The dashboard needs a signed-in session; this script stubs only the account
endpoints (/auth/*) in the browser. Every feed, seal check and on-chain proof
shown in the shots is real data from the live API.
"""
import os, sys, time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://getpulsedata.online"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)

AUTH_STUB = r"""(()=>{const of=window.fetch;window.fetch=async(u,o)=>{u=String(u);
if(u.includes('/auth/me'))return new Response(JSON.stringify({email:'demo@pulse.dev',name:'Demo'}),{status:200});
if(u.includes('/auth/keys'))return new Response(JSON.stringify({keys:[]}),{status:200});
if(u.includes('/auth/categories')){const c=await (await of('/data/categories')).json();
 for(const k in c)c[k].enabled=['crypto','regulatory','politics','news'].includes(k);
 return new Response(JSON.stringify(c),{status:200});}
return of(u,o);};})();"""

def shot(page, name, **kw):
    page.screenshot(path=os.path.join(OUT, name), **kw)
    print("wrote", name)

with sync_playwright() as p:
    b = p.chromium.launch()
    d = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    pg = d.new_page()
    pg.goto(BASE + "/", wait_until="networkidle"); time.sleep(2)
    shot(pg, "landing.png")

    pg.add_init_script(AUTH_STUB)
    pg.goto(BASE + "/dashboard?feed=regulatory", wait_until="networkidle")
    pg.wait_for_selector(".pv-seal", timeout=60000); time.sleep(1)
    el = pg.query_selector(".preview-content")
    el.scroll_into_view_if_needed(); time.sleep(.5)
    shot(pg, "regulatory-feed.png")
    box = pg.query_selector(".preview-content").bounding_box()
    shot(pg, "seal.png", clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": min(box["height"], 520)})


    m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(BASE + "/", wait_until="networkidle"); time.sleep(2)
    shot(mp, "mobile.png")
    b.close()
