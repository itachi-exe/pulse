#!/usr/bin/env python3
"""Build the voiceover for the BRIX film.

One edge-tts call per beat (retry + Kokoro fallback), exact WordBoundary
timings from the synthesizer itself, numpy assembly with a fixed gap between
beats, one loudnorm pass over the whole track.

  work/vo.wav          final voiceover, 48k mono
  work/manifest.json   beats with start/end on the final timeline + word cues
  work/captions.srt    captions from the synthesizer's own timings
"""
import asyncio
import json
import os
import re
import subprocess
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
PARTS = os.path.join(WORK, "vo_parts")
SR = 48000
os.makedirs(PARTS, exist_ok=True)

CFG = json.load(open(os.path.join(HERE, "beats.json")))
VOICE = CFG["voice"]
RATE = CFG["rate"]
GAP = CFG["gap"]


def ff(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return r


def decode(mp3, wav):
    ff(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", mp3,
        "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", wav])


async def tts_edge(text, out_mp3):
    """Synthesize and return word cues. boundary=WordBoundary is required:
    the library defaults to SentenceBoundary, which yields no word events."""
    import edge_tts
    words = []
    audio = bytearray()
    com = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    async for chunk in com.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            words.append({"w": chunk["text"],
                          "start": chunk["offset"] / 1e7,
                          "end": (chunk["offset"] + chunk["duration"]) / 1e7})
    if not audio:
        raise RuntimeError("edge-tts returned no audio")
    with open(out_mp3, "wb") as f:
        f.write(audio)
    return words


def tts_kokoro(text, out_mp3):
    """Offline fallback: Kokoro British female. No word events, so captions for
    that beat fall back to even distribution inside the sentence."""
    from kokoro_onnx import Kokoro
    k = Kokoro("/tmp/kokoro/kokoro-v1.0.onnx", "/tmp/kokoro/voices-v1.0.bin")
    samples, sr = k.create(text, voice="bf_emma", speed=1.0, lang="en-gb")
    raw = out_mp3.replace(".mp3", "_k.wav")
    sf.write(raw, samples, sr)
    ff(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", raw,
        "-ac", "1", "-ar", "24000", "-b:a", "64k", out_mp3])
    os.unlink(raw)
    return []


def even_words(text, dur):
    """Fallback cues when a beat was synthesized without word events."""
    ws = text.split()
    step = dur / max(len(ws), 1)
    return [{"w": w, "start": i * step, "end": (i + 1) * step - 0.02}
            for i, w in enumerate(ws)]


def build():
    parts, bm = [], []
    cursor = 0.0
    for beat in CFG["beats"]:
        bid = beat["id"]
        print("beat", bid, beat["scene"], flush=True)
        mp3 = os.path.join(PARTS, bid + ".mp3")
        wav = os.path.join(PARTS, bid + ".wav")
        wj = os.path.join(PARTS, bid + ".words.json")
        if not (os.path.exists(mp3) and os.path.getsize(mp3) > 2000
                and os.path.exists(wj) and len(json.load(open(wj))) > 0):
            for attempt in range(6):
                try:
                    words = asyncio.run(tts_edge(beat["narration"], mp3))
                    json.dump(words, open(wj, "w"))
                    print(f"  edge ok, {len(words)} word cues", flush=True)
                    break
                except Exception as e:
                    print(f"  edge attempt {attempt}: {type(e).__name__} {str(e)[:60]}", flush=True)
                    time.sleep(3 + attempt * 4)
            else:
                print("  FALLBACK kokoro", flush=True)
                tts_kokoro(beat["narration"], mp3)
                json.dump([], open(wj, "w"))
        else:
            print("  cached", flush=True)
        decode(mp3, wav)
        data, _ = sf.read(wav, dtype="float32")
        dur = len(data) / SR
        words = json.load(open(wj)) if os.path.exists(wj) else []
        if not words:
            words = even_words(beat["narration"], dur)
        start, end = cursor, cursor + dur
        bm.append({"id": bid, "kind": beat["kind"], "scene": beat["scene"],
                   "narration": beat["narration"], "start": round(start, 3),
                   "end": round(end, 3), "dur": round(dur, 3), "words": words})
        parts.append(data)
        parts.append(np.zeros(int(GAP * SR), dtype="float32"))
        cursor = end + GAP

    track = np.concatenate(parts)
    total = len(track) / SR
    raw_wav = os.path.join(WORK, "vo_raw.wav")
    sf.write(raw_wav, track, SR)

    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", raw_wav, "-af",
         "loudnorm=I=-15.5:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    m = json.loads(probe.stderr[probe.stderr.rfind("{"):probe.stderr.rfind("}") + 1])
    print("loudness in:", m["input_i"], m["input_tp"], flush=True)
    vo = os.path.join(WORK, "vo.wav")
    ff(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", raw_wav, "-af",
        ("loudnorm=I=-15.5:TP=-2.0:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s"
         ":measured_thresh=%s:offset=%s:linear=true") % (
            m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"]),
        "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", vo])

    for i, b in enumerate(bm):
        b["win_end"] = bm[i + 1]["start"] if i + 1 < len(bm) else round(total, 3)
        b["win_dur"] = round(b["win_end"] - b["start"], 3)
    json.dump({"voice": VOICE, "rate": RATE, "gap": GAP, "total": round(total, 3),
               "beats": bm}, open(os.path.join(WORK, "manifest.json"), "w"), indent=1)

    def ts(t):
        h = int(t // 3600); mn = int((t % 3600) // 60); se = t % 60
        return f"{h:02d}:{mn:02d}:{se:06.3f}".replace(".", ",")

    srt, n = [], 0
    for b in bm:
        # Display text comes from the script (it carries punctuation); the
        # synthesizer's word events only supply timing. They are 1:1 in order.
        toks = re.findall(r"\S+", b["narration"])
        cues = b["words"]
        if len(toks) != len(cues):
            print(f"  WARN {b['id']}: {len(toks)} script words vs {len(cues)} cues, "
                  "using synthesizer text")
            toks = [c["w"] for c in cues]
        words = [dict(c, w=t) for c, t in zip(cues, toks)]
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) >= 7 or (w["w"].strip().endswith((".", "?", "!", ",")) and len(cur) >= 4):
                chunks.append(cur); cur = []
        if cur:
            chunks.append(cur)
        for i, c in enumerate(chunks):
            n += 1
            st = b["start"] + c[0]["start"]
            en = b["start"] + c[-1]["end"]
            if i + 1 < len(chunks):
                en = min(en, b["start"] + chunks[i + 1][0]["start"] - 0.05)
            en = min(en, b["win_end"] - 0.05)
            txt = " ".join(x["w"] for x in c).replace("--", ",").replace(" - ", ", ")
            srt.append(f"{n}\n{ts(st)} --> {ts(max(en, st + 0.4))}\n{txt}\n")
    open(os.path.join(WORK, "captions.srt"), "w").write("\n".join(srt))
    wc = sum(len(b["narration"].split()) for b in bm)
    print(f"total {total:.2f}s  captions {n}  words {wc}  wpm {wc/total*60:.1f}")


if __name__ == "__main__":
    build()
