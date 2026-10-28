#!/usr/bin/env python3
"""Clips + voiceover + captions -> out/pulse_bli_demo.mp4"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); WRK = os.path.join(HERE, "work")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
M = json.load(open(os.path.join(WRK, "manifest.json")))
ins, parts = [], []
for i, b in enumerate(M["beats"]):
    c = os.path.join(WRK, "clips", b["scene"] + ".webm"); meta = json.load(open(c + ".json"))
    ins += ["-i", c]
    fi = "fade=t=in:st=0:d=0.25," if i else ""
    parts.append(f"[{i}:v]trim=start={meta['lead']}:duration={b['win_dur']},setpts=PTS-STARTPTS,fps=30,scale=1920:1080:flags=lanczos,"
                 f"{fi}fade=t=out:st={b['win_dur']-0.25:.3f}:d=0.25,format=yuv420p[v{i}]")
n = len(M["beats"])
style = ("FontName=Onest,FontSize=19,PrimaryColour=&H00E8EDF0,OutlineColour=&H000B0C0D,BackColour=&H000B0C0D,"
         "BorderStyle=4,Outline=0,Shadow=0,MarginV=28,Alignment=2")
srt = os.path.join(WRK, "captions.srt").replace(":", r"\:")
fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[pic];[pic]subtitles='{srt}':force_style='{style}'[v]"
cmd = ["ffmpeg", "-y", "-loglevel", "error", *ins, "-i", os.path.join(WRK, "vo.wav"), "-filter_complex", fc,
       "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", os.path.join(OUT, "pulse_bli_demo.mp4")]
subprocess.run(cmd, check=True); print("done")
