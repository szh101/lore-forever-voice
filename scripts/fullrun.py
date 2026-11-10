"""The full run's driver: take each finished translation batch, rebuild the manifest, record a few clips, repeat.

  python scripts/fullrun.py --voice <documentary-voice> --model <qwen3-tts dir> [--python <mlx venv python>]

work/tr-out/full-NN.zh.json (n, s, sec_b per id) -> translations/zhCN/full-NN.json (n, s, sec[0].b), new terms
-> glossary/new-terms-full.tsv. One process at a time touches manifest/clips.jsonl, so it can be stopped and
started again at any point. Stops when every batch is in and nothing is left to record.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN, OUT, TR = ROOT / "work" / "tr-in", ROOT / "work" / "tr-out", ROOT / "translations" / "zhCN"


def take_batches():
    done = 0
    for src in sorted(IN.glob("full-*.en.json")):
        n = src.name.split(".")[0]
        zh, dest = OUT / f"{n}.zh.json", TR / f"{n}.json"
        if dest.exists():
            done += 1
            continue
        if not zh.exists():
            continue
        try:
            en, t = json.loads(src.read_text()), json.loads(zh.read_text())
        except json.JSONDecodeError:
            continue   # still being written
        ok = all(k in t and t[k].get("n") and t[k].get("s") and (("sec_b" in t[k]) == ("sec_b" in v))
                 for k, v in en.items())
        if not ok or set(k for k in t if not k.startswith("_")) != set(en):
            continue   # not finished yet
        out = {}
        for k, v in t.items():
            if k.startswith("_"):
                continue
            out[k] = {"n": v["n"], "s": v["s"]}
            if "sec_b" in v:
                out[k]["sec"] = [{"b": v["sec_b"]}]
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        with open(ROOT / "glossary" / "new-terms-full.tsv", "a", encoding="utf-8") as f:
            for term in t.get("_new_terms", []):
                f.write("\t".join(map(str, term)) + f"\t{n}\n")
        print(f"took {n}: {len(out)} entries", flush=True)
        done += 1
    return done, len(list(IN.glob("full-*.en.json")))


TAG = "zhCN-1.4.0-1"
NOTES = """Lore Forever 中文女声旁白（插件文字保持英文）——全量版，录制中，每录完一个包就更新一次。

Chinese female narration for Lore Forever, read over its English text: the 9 lore packs' overview stories
(5,165 recordings when complete). Works on Lore Forever 1.3.0 and 1.4.0. Quest giver dialogue is not included.

This release is updated as each pack finishes recording; release-manifest.json lists what is in it now
(sha256, sizes, and per pack how many recordings). Packs not yet complete still work: stories they lack fall
back to your next narrator. Install: INSTALL.md (replace the pilot-1 folders). Details: REPORT.md."""


def complete_packs(rows):
    by = {}
    for r in rows:
        by.setdefault(r["pack"], []).append(r.get("status") in ("recorded", "check"))
    return sorted(p for p, v in by.items() if all(v))


def publish(a, why):
    """Build every pack from what is recorded, self-check, and replace the release's assets."""
    build, dist = ROOT / "build-full", ROOT / "dist" / TAG
    for d in (build, dist):
        shutil.rmtree(d, ignore_errors=True)
    run = lambda *c: subprocess.run(list(c), check=True, cwd=ROOT)
    run(a.lua_python, "scripts/build.py", "packs", "--out", str(build))
    run(a.lua_python, "scripts/selfcheck.py", "--build", str(build), "--addons", "addons",
        "--json", str(build / "selfcheck.json"))
    run(a.lua_python, "scripts/release.py", "--build", str(build), "--dist", "dist", "--tag", TAG)
    files = [str(f) for f in sorted(dist.iterdir())]
    if subprocess.run(["gh", "release", "view", TAG], cwd=ROOT, capture_output=True).returncode:
        run("gh", "release", "create", TAG, *files, "--title", "Chinese female narration (full run)", "--notes", NOTES)
    else:
        run("gh", "release", "upload", TAG, *files, "--clobber")
    print(f"published {TAG}: {why}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--lua-python", default=sys.executable, help="a python with lupa, for the self-check")
    ap.add_argument("--step", type=int, default=30, help="clips recorded between batch checks")
    a = ap.parse_args()
    state = ROOT / "work" / "published-packs.json"
    while True:
        done, total = take_batches()
        subprocess.run([a.python, str(ROOT / "scripts" / "build.py"), "prepare", "--scope", "all"], check=True, cwd=ROOT)
        rows = [json.loads(l) for l in (ROOT / "manifest" / "clips.jsonl").read_text().splitlines() if l.strip()]
        left = sum(1 for r in rows if r.get("zh_text") and r.get("status") not in ("recorded", "check"))
        print(f"batches {done}/{total}, clips to record {left}", flush=True)
        if done == total:
            ready = complete_packs(rows)
            before = json.loads(state.read_text()) if state.exists() else []
            if ready != before and set(ready) - set(before):
                try:
                    publish(a, "complete: " + ", ".join(ready))
                    state.write_text(json.dumps(ready))
                except subprocess.CalledProcessError as e:
                    print(f"publish failed ({e}); recording goes on, next pack retries", flush=True)
        if left:
            subprocess.run([a.python, str(ROOT / "scripts" / "tts_zh.py"), "--voice", a.voice, "--model", a.model,
                            "--limit", str(a.step)], check=True, cwd=ROOT)
        elif done == total:
            print("full run recorded", flush=True)
            return
        else:
            time.sleep(120)


if __name__ == "__main__":
    main()
