# Pulse — design.md

## Product Feel
Dark terminal infrastructure. rig.ai energy. Not a startup, a tool that serious engineers trust.
The hero is the product working, not a description of it.

## Audience
AI engineers, agent builders, DeFi developers who have been burned by stale data.

## Accent
mint-green #75e5b0 (AI/agent domain)

## Copy Voice
Sparse. Technical. Direct. One line per idea. Numbers over adjectives.
No em-dashes. No exclamation marks. No "revolutionary".

## Screens In Order
1. Hero — live terminal feed (Pulse vs baseline, updating every 10s)
2. Problem — 4 numbered problems agents face with blind data
3. Architecture — how Pulse works (visual flow diagram)
4. Comparison — side by side: baseline decision vs Pulse decision
5. Stats — latency, sources, confidence
6. Install — pip install + curl command + one-line SDK usage
7. Footer

## Reference Notes
### rig.ai
- Dark #0a0a0a bg, green terminal accent
- Hero: ASCII terminal block showing product in action (not marketing copy)
- Problem section: numbered 001/002/003/004, one problem per block, icon + title + 2 sentences
- Comparison bars: visual specs (latency, cost, size) — simple bar charts with numbers
- Feature grid: numbered [01][02][03] in brackets, terse descriptions
- No hero image — the terminal IS the hero
- Stats block at fold: 4 key numbers inline
- One CTA above fold, one at bottom. That's it.
- Scrolling marquee for feature keywords
- ASCII logo in terminal

### What we do differently
- Our hero is a LIVE feed updating every 10 seconds from real data
- Side by side: baseline vs Pulse making a decision on the same question
- Confidence score visible as a real number, not a bar

## States To Cover
- Connecting to Pulse API (skeleton)
- Live data flowing (animated)
- API unreachable (graceful fallback with static demo data)
- Mobile responsive

## User Flow
Land → see live Pulse catching wrong decision → understand why → copy install command → done
