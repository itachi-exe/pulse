#!/usr/bin/env python3
"""Record every scene of the Pulse film at 1920x1080, one webm per beat.

  .venv/bin/python record.py            # all scenes
  .venv/bin/python record.py curl seal  # just these

Live scenes (landing, dashboard) drive the real site. Terminal scenes replay
output captured from real runs (work/out_*.txt). Durations come from the
voiceover manifest so picture and voice line up.
"""
import html, json, os, shutil, sys, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
WRK = os.path.join(HERE, "work"); CLIPS = os.path.join(WRK, "clips"); os.makedirs(CLIPS, exist_ok=True)
M = json.load(open(os.path.join(WRK, "manifest.json")))
DUR = {b["scene"]: b["win_dur"] for b in M["beats"]}
BASE = "https://getpulsedata.online"
W, H = 1920, 1080
out = lambda n: open(os.path.join(WRK, f"out_{n}.txt")).read().rstrip("\n")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Onest:wght@300;400;500;600;700;900&family=Space+Mono:wght@400;700&display=swap');
:root{--bg:#0d0c0b;--ink:#f0ede8;--ink2:#c8c4bc;--muted:#807a72;--faint:#38342e;--acc:#75e5b0;--bad:#ff7a6b}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;background:var(--bg);color:var(--ink);font-family:Onest,sans-serif;overflow:hidden}
.wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 200px}
.kick{font-family:'Space Mono',monospace;font-size:22px;letter-spacing:.18em;text-transform:uppercase;color:var(--acc);margin-bottom:36px;opacity:0;animation:in .6s .2s forwards}
.term{background:#141210;border:1px solid var(--faint);border-radius:18px;padding:44px 52px;font-family:'Space Mono',monospace;font-size:25px;line-height:1.62;color:var(--ink2);white-space:pre-wrap;word-break:break-all;box-shadow:0 40px 120px rgba(0,0,0,.5);opacity:0;animation:in .5s .1s forwards;max-height:860px;overflow:hidden}
.bar{display:flex;gap:10px;margin-bottom:26px}.bar i{width:14px;height:14px;border-radius:50%;background:var(--faint)}
.p{color:var(--acc)}.ok{color:var(--acc)}.bad{color:var(--bad)}.dim{color:var(--muted)}.hi{color:var(--ink)}
.cur{display:inline-block;width:14px;height:28px;background:var(--acc);vertical-align:-5px;animation:blink 1s steps(1) infinite}
@keyframes in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes blink{50%{opacity:0}}
.ln{opacity:0;transition:opacity .25s}.ln.on{opacity:1}
"""

def page_html(body, script=""):
    return f"<!doctype html><html><head><meta charset=utf-8><style>{CSS}</style></head><body>{body}<script>{script}</script></body></html>"

def esc(s): return html.escape(s)

def term_scene(kicker, cmd, lines, start_ms, step_ms, cls=None):
    """Type a command, then reveal output lines one by one."""
    cls = cls or {}
    rows = "".join(f'<div class="ln {cls.get(i, "")}">{esc(l) if l else "&nbsp;"}</div>' for i, l in enumerate(lines))
    body = f'<div class="wrap"><div class="kick">{kicker}</div><div class="term"><div class="bar"><i></i><i></i><i></i></div><div><span class="p">$ </span><span id="cmd"></span><span class="cur" id="cur"></span></div><div id="o">{rows}</div></div></div>'
    js = f"""const c={json.dumps(cmd)};let i=0;const el=document.getElementById('cmd');
    setTimeout(function t(){{el.textContent=c.slice(0,++i);if(i<c.length)setTimeout(t,38);else{{document.getElementById('cur').style.display='none';
      const L=[...document.querySelectorAll('.ln')];L.forEach((l,k)=>setTimeout(()=>l.classList.add('on'),{start_ms}+k*{step_ms}));}}}},700);"""
    return page_html(body, js)

def hook_html():
    body = """<div class="wrap" style="align-items:center;text-align:center">
    <div style="width:1200px;text-align:left">
     <div class="ln" id="q" style="margin-left:auto;width:fit-content;background:#1c1a17;border:1px solid var(--faint);border-radius:26px 26px 6px 26px;padding:28px 36px;font-size:40px;font-weight:500">What did the SEC do this week?</div>
     <div class="ln" id="a" style="margin-top:34px;width:fit-content;max-width:1000px;border-radius:26px 26px 26px 6px;padding:28px 36px;font-size:34px;line-height:1.45;color:var(--ink2);background:#141210;border:1px solid var(--faint)"><span id="at"></span></div>
     <div class="ln" id="tag" style="margin-top:60px;font-family:'Space Mono',monospace;font-size:24px;color:var(--bad);letter-spacing:.06em">Training data, months old. Sounds sure. Can't be checked.</div>
    </div></div>"""
    js = """const on=(id,t)=>setTimeout(()=>document.getElementById(id).classList.add('on'),t);
    on('q',500);on('a',1900);
    const s="As of my last update, the SEC had been focusing on crypto enforcement and climate disclosure rules. I don't have information about this week.";
    let i=0;setTimeout(function t(){document.getElementById('at').textContent=s.slice(0,++i);if(i<s.length)setTimeout(t,26)},2100);on('tag',6600);"""
    return page_html(body, js)

def seal_html():
    d = "712e1c540b3321fdbc9064377d53d00b6719542be0cf0c4951324da2eab308ba"
    tx = "0x6791b847c3fb18e73de20c0352788810b8fb2a1c2e59e08e00d1bb267d2f70d4"
    box = "background:#141210;border:1px solid var(--faint);border-radius:18px;padding:30px 36px;font-family:'Space Mono',monospace"
    body = f"""<div class="wrap"><div class="kick">How a day is sealed</div>
    <div style="display:flex;gap:28px;align-items:stretch">
      <div class="ln" id="s1" style="{box};flex:1"><div class="dim" style="font-size:19px;margin-bottom:14px">80 ITEMS</div>
        <div style="font-size:21px;line-height:1.9;color:var(--ink2)">sha256(item 1) b6db8e59…<br>sha256(item 2) 2799f50b…<br>sha256(item 3) eda7aece…<br><span class="dim">… 77 more</span></div></div>
      <div class="ln" id="s2" style="{box};flex:1"><div class="dim" style="font-size:19px;margin-bottom:14px">ONE DIGEST FOR THE DAY</div>
        <div style="font-size:23px;line-height:1.6;color:var(--acc);word-break:break-all">{d}</div></div>
    </div>
    <div class="ln" id="s3" style="{box};margin-top:28px"><div class="dim" style="font-size:19px;margin-bottom:14px">WRITTEN ON CHAIN · 0G GALILEO · BLOCK 62574301</div>
      <div style="font-size:22px;color:var(--ink);word-break:break-all">PULSE-REG:v1:2026-10-28:{d}</div>
      <div class="dim" style="font-size:19px;margin-top:14px">tx {tx}</div></div>
    </div>"""
    js = "[['s1',300],['s2',2600],['s3',4600]].forEach(([i,t])=>setTimeout(()=>document.getElementById(i).classList.add('on'),t));"
    return page_html(body, js)

def end_html():
    body = """<div class="wrap" style="align-items:center;text-align:center">
     <div class="ln" id="e1" style="font-size:150px;font-weight:700;letter-spacing:-.04em">Pulse</div>
     <div class="ln" id="e2" style="font-size:44px;color:var(--ink2);margin-top:18px">The regulatory feed for AI agents, with proof.</div>
     <div class="ln" id="e3" style="margin-top:70px;font-family:'Space Mono',monospace;font-size:30px;color:var(--acc)">getpulsedata.online</div>
     <div class="ln" id="e4" style="margin-top:22px;font-family:'Space Mono',monospace;font-size:21px;color:var(--muted)">38 regulatory sources · 1,221 sources total · anchored daily on-chain</div></div>"""
    js = "[['e1',200],['e2',1200],['e3',2600],['e4',3400]].forEach(([i,t])=>setTimeout(()=>document.getElementById(i).classList.add('on'),t));"
    return page_html(body, js)

AUTH_STUB = open(os.path.join(HERE, "auth_stub.js")).read() if os.path.exists(os.path.join(HERE, "auth_stub.js")) else ""

def smooth_scroll(pg, to, ms):
    pg.evaluate(f"""(()=>{{const s=scrollY,d={to}-s,t0=performance.now();
      function f(t){{const k=Math.min(1,(t-t0)/{ms});const e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;scrollTo(0,s+d*e);if(k<1)requestAnimationFrame(f)}}requestAnimationFrame(f)}})()""")

def run_scene(browser, name):
    dur = DUR[name]
    vw, vh = (1280, 720) if name in ("landing", "dashboard") else (W, H)  # live UI: smaller viewport = bigger text
    ctx = browser.new_context(viewport={"width": vw, "height": vh}, record_video_dir=os.path.join(WRK, "raw"),
                              record_video_size={"width": vw, "height": vh})
    pg = ctx.new_page()
    lead = 0.0  # seconds of video before the scene's t=0, trimmed later
    t0 = time.time()
    if name == "hook":
        pg.set_content(hook_html())
    elif name == "curl":
        lines = out("curl").split("\n")[:24]
        pg.set_content(term_scene("No key, one call", "curl getpulsedata.online/data/feed/regulatory", lines, 300, 130))
    elif name == "verify":
        lines = out("verify").split("\n")
        cls = {i: "hi" if "ok" in l else "" for i, l in enumerate(lines)}; cls[len(lines) - 1] = "ok"
        pg.set_content(term_scene("Check it yourself, standard library only", "python verify.py 2026-10-28", lines, 1600, 1100, cls))
    elif name == "tamper":
        lines = out("tamper").split("\n")
        cls = {i: ("bad" if ("MISMATCH" in l or "False" in l) else "hi") for i, l in enumerate(lines)}
        pg.set_content(term_scene("Attack: edit a headline, rewrite every hash", "python tamper_test.py   # on a copy of the database", lines, 600, 1250, cls))
    elif name == "agents":
        lines = out("mcp").split("\n")
        pg.set_content(term_scene("Agents call it as a tool (MCP)", 'pulse_regulatory(query="SEC")', lines, 500, 700, {0: "dim"}))
    elif name == "seal":
        pg.set_content(seal_html())
    elif name == "end":
        pg.set_content(end_html())
    elif name == "landing":
        pg.goto(BASE + "/", wait_until="networkidle"); pg.wait_for_timeout(1200)
        lead = time.time() - t0
        pg.wait_for_timeout(1800); smooth_scroll(pg, 900, 3200); pg.wait_for_timeout(3600)
    elif name == "dashboard":
        pg.add_init_script(AUTH_STUB)
        pg.goto(BASE + "/dashboard?feed=regulatory", wait_until="networkidle")
        pg.wait_for_selector(".pv-seal", timeout=60000); pg.wait_for_timeout(600)
        y = pg.evaluate("document.querySelector('.pv-seal').getBoundingClientRect().top+scrollY-170")
        pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(500)
        lead = time.time() - t0
        pg.wait_for_timeout(2200); smooth_scroll(pg, y + 200, 3000); pg.wait_for_timeout(3200)
    if name not in ("landing", "dashboard"):
        lead = time.time() - t0
    remain = dur + 0.3 - (time.time() - t0 - lead)
    if remain > 0: pg.wait_for_timeout(int(remain * 1000))
    path = pg.video.path(); ctx.close()
    dst = os.path.join(CLIPS, f"{name}.webm"); shutil.move(path, dst)
    json.dump({"lead": round(lead, 3), "dur": dur}, open(dst + ".json", "w"))
    print(f"{name}: lead {lead:.2f}s dur {dur:.2f}s")

if __name__ == "__main__":
    want = sys.argv[1:] or [b["scene"] for b in M["beats"]]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-gpu"])
        for s in want: run_scene(b, s)
        b.close()
