"""Record the zhCN narration for every manifest clip that has text and no audio yet (resumable).

Runs on an Apple Silicon Mac with mlx-audio (the documentary voice, Qwen3-TTS 1.7B Base voice cloning):

  <venv with mlx-audio>/bin/python scripts/tts_zh.py --voice <documentary-voice dir> --model <model dir> \
      --manifest manifest/clips.jsonl --audio work/audio [--only KEY ...] [--limit N]

The voice folder holds reference.wav, transcript.txt and voice.json (never copied into this repo). Each clip:
text split at sentence ends (<= 600 chars per call), 0.25 s silence between pieces, 24 kHz mono WAV ->
leading/trailing silence trimmed, loudness normalised to -19 LUFS (the English female packs measure about -19),
44.1 kHz mono MP3 at 64 kb/s like the English packs. The manifest row gets audio, duration and status.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import read_jsonl, write_jsonl  # noqa: E402

SR = 24000
GAP = 0.25
CHUNK = 600   # characters per generate call (voice.json max_chars_per_call is 1200; speak.py uses half)


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def chunks(text, limit=CHUNK):
    parts, cur = [], ""
    for s in re.split(r"(?<=[。！？!?；;…])\s*", text.strip()):
        if not s:
            continue
        if cur and len(cur) + len(s) > limit:
            parts.append(cur)
            cur = ""
        cur += s
    return [p for p in parts + [cur] if p.strip()]


def duration_of(path):
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", out.stderr)
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def encode(wav, mp3):
    mp3.parent.mkdir(parents=True, exist_ok=True)
    trim = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05"
    af = f"{trim},areverse,{trim},areverse,loudnorm=I=-19:TP=-1.5:LRA=11,aresample=44100"
    out = ["-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k", str(mp3)]
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-af", af] + out)
    if r.returncode == 0:
        return
    # ffmpeg 7.1 aborts on some files in this filter chain (assertion in ffmpeg_filter.c).
    # Trim the same silence here (-50 dB, keep 0.05 s) and let ffmpeg only normalise.
    d, sr = sf.read(wav, dtype="float32")
    loud = np.flatnonzero(np.abs(d) > 10 ** (-50 / 20))
    if not loud.size:
        raise RuntimeError(f"{wav} is silent")
    keep = int(sr * 0.05)
    tmp = wav.with_suffix(".trim.wav")
    sf.write(tmp, d[max(loud[0] - keep, 0):loud[-1] + keep + 1], sr)
    try:
        subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp), "-af",
                        "loudnorm=I=-19:TP=-1.5:LRA=11,aresample=44100"] + out, check=True)
    finally:
        tmp.unlink(missing_ok=True)


# Speaking rate outside this means a cut-off or a loop (the pilot ran 5.1-6.1 chars/s).
CPS_LOW, CPS_HIGH = 3.8, 7.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--manifest", default="manifest/clips.jsonl")
    ap.add_argument("--audio", default="work/audio")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", action="store_true", help="re-record rows that already have audio")
    a = ap.parse_args()

    voice = Path(a.voice)
    meta = json.loads((voice / "voice.json").read_text(encoding="utf-8"))
    ref_text = (voice / "transcript.txt").read_text(encoding="utf-8").strip()
    if ref_text != meta["transcript"].strip():
        sys.exit("transcript.txt and voice.json transcript differ")
    if hashlib.sha256((voice / "reference.wav").read_bytes()).hexdigest() != meta["reference_sha256"]:
        sys.exit("reference.wav does not match voice.json reference_sha256")
    installed = Path(a.model) / "installed.json"
    if installed.exists():
        m = json.loads(installed.read_text())
        if m.get("revision") != meta["model_revision"]:
            sys.exit(f"model revision {m.get('revision')} != voice.json {meta['model_revision']}")
    s = meta["settings"]

    rows = read_jsonl(a.manifest)
    want = ("pending", "recorded", "check") if a.redo else ("pending",)   # never "retranslate": stale Chinese
    todo = [r for r in rows if r.get("zh_text") and r.get("status") in want
            and (not a.only or r["id"] in a.only)]
    seen = set()
    todo = [r for r in todo if not (r["id"] in seen or seen.add(r["id"]))]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(todo)} clips to record")
    if not todo:
        return

    from mlx_audio.tts.utils import load_model
    model = load_model(a.model)
    tries = {}
    audio = Path(a.audio)
    t0 = time.time()
    i = 0
    while i < len(todo):
        r = todo[i]
        i += 1
        pieces = []
        for part in chunks(r["zh_text"]):
            res = list(model.generate(text=part, ref_audio=str(voice / "reference.wav"), ref_text=ref_text,
                                      lang_code="Chinese", temperature=s["temperature"],
                                      # ~2.3 codec tokens a character: a cap keeps a short heading from running on
                                      max_tokens=min(s["max_tokens"], max(48, 6 * len(part))),
                                      stream=False, verbose=False))
            pieces += [np.asarray(x.audio, dtype=np.float32).reshape(-1) for x in res]
            pieces.append(np.zeros(int(SR * GAP), dtype=np.float32))
        wav = audio / "wav" / r["pack"] / (r["stem"] + ".wav")
        wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(wav, np.concatenate(pieces[:-1]), SR)
        mp3 = audio / "mp3" / r["pack"] / (r["stem"] + ".mp3")
        try:
            encode(wav, mp3)
            dur = duration_of(mp3)
        except Exception as e:   # one bad clip must not stop the run
            print(f"  {r['id']}: encoding failed ({e})", flush=True)
            dur = None
        cps = round(len(r["zh_text"]) / dur, 2) if dur else None
        low, high = (CPS_LOW, CPS_HIGH) if len(r["zh_text"]) > 12 else (1.5, 10.0)   # a heading: a few words
        if cps is None or not (low <= cps <= high):
            tries[r["id"]] = tries.get(r["id"], 0) + 1
            if tries[r["id"]] < 3:   # a cut-off or a loop: record it again
                print(f"  {r['id']}: {cps} chars/s is outside {low}-{high}, again", flush=True)
                todo.append(r)
                continue
            flag = "check"
        else:
            flag = "recorded"
        # An id in two packs (the same story) is recorded once; every row of it gets the file.
        for row in rows:
            if row["id"] == r["id"] and row.get("zh_text") == r["zh_text"]:
                row.update(audio=str(mp3.relative_to(audio)), duration=round(dur, 3) if dur else None, status=flag,
                           chars_per_sec=cps, recorded_text_sha=hashlib.sha1(r["zh_text"].encode()).hexdigest()[:12])
        write_jsonl(a.manifest, rows)   # after every clip: safe to stop and resume
        el = time.time() - t0
        print(f"[{i}/{len(todo)}] {r['id']} {(dur or 0):.1f}s audio, {len(r['zh_text'])} chars, "
              f"elapsed {el/60:.1f} min, eta {el/i*(len(todo)-i)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
