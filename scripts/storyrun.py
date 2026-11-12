"""The second run's driver, queued after the overview run (scripts/fullrun.py): complete stories (scripts/stories.py),
then quest dialogue, recaps and book pages (scripts/extras.py).

  <mlx venv>/python scripts/storyrun.py --voice <documentary-voice> --model <qwen3-tts dir> --lua-python <lua> \
      [--after <pid>] [--tag zhCN-1.4.0-1]

Each turn: take finished translation batches, rebuild manifest/stories.jsonl, cut a few more overviews where their
section 1 starts (local forced aligner), record 30 clips. A pack is published again (the release's assets
replaced) each time all its stories are recorded. Stops when every batch is in and nothing is left to record or cut.
Safe to stop and start at any point, like fullrun.py.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fullrun  # noqa: E402


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--lua-python", default=sys.executable)
    ap.add_argument("--tag", default=fullrun.TAG)
    ap.add_argument("--after", type=int, help="wait for this process (the overview run) to finish first")
    ap.add_argument("--step", type=int, default=30)
    a = ap.parse_args()
    if a.after:
        print(f"waiting for process {a.after} (the overview run)", flush=True)
        while alive(a.after):
            time.sleep(60)
    py = lambda *args, **kw: subprocess.run([a.python, str(ROOT / "scripts" / args[0]), *args[1:]], cwd=ROOT, **kw)
    state = ROOT / "work" / f"published-stories-{a.tag}.json"
    while True:
        py("stories.py", "take")
        py("stories.py", "prepare", check=True)
        py("extras.py", "take")
        py("extras.py", "prepare", check=True)
        cut = py("stories.py", "split", "--limit", "150", capture_output=True, text=True)
        lines = cut.stdout.strip().splitlines()
        print(lines[-2] if len(lines) > 1 else cut.stderr[-500:], flush=True)
        rows = [json.loads(l) for l in (ROOT / "manifest" / "stories.jsonl").read_text().splitlines() if l.strip()]
        extras = [json.loads(l) for l in (ROOT / "manifest" / "extras.jsonl").read_text().splitlines() if l.strip()]
        story_left = sum(1 for r in rows if r["status"] == "pending")
        rows += [r for r in extras if r["status"] != "no source"]   # (no English to translate: left out)
        left = sum(1 for r in rows if r["status"] == "pending")
        waiting = sum(1 for r in rows if r["status"] in ("untranslated", "retranslate"))
        uncut = "cut this run: 150" in cut.stdout   # a full slice: more overviews to cut
        by = {}
        for r in rows:
            by.setdefault(r["pack"], []).append(r["status"] in ("recorded", "check"))
        ready = sorted(p for p, v in by.items() if all(v))
        before = json.loads(state.read_text()) if state.exists() else []
        print(f"stories+extras: to record {left}, waiting for a translation {waiting}, packs complete {len(ready)}",
              flush=True)
        if set(ready) - set(before) or (not left and not waiting and not uncut and ready != before):
            try:
                fullrun.publish(a, "complete stories: " + ", ".join(ready))
                state.write_text(json.dumps(ready))
            except subprocess.CalledProcessError as e:
                print(f"publish failed ({e}); recording goes on, the next pack retries", flush=True)
        if left:   # complete stories first, then quest dialogue, recaps and books
            manifest = "manifest/stories.jsonl" if story_left else "manifest/extras.jsonl"
            py("tts_zh.py", "--voice", a.voice, "--model", a.model, "--manifest", manifest,
               "--limit", str(a.step)).returncode and time.sleep(30)
        elif waiting or uncut:
            time.sleep(120 if waiting else 1)
        else:
            if ready != before:   # the last publish failed: try again
                time.sleep(300)
                continue
            print("complete stories recorded", flush=True)
            return


if __name__ == "__main__":
    main()
