"""After a Lore Forever update: find what is new or changed, and hand it out for translation (UPDATING.md).

  python scripts/update.py status              what the manifest says now (no changes)
  python scripts/update.py export [--size 150] rebuild the manifest, then write the entries that need a translation
                                               to work/tr-in/upd-YYYYMMDD-NN.en.json

Each exported entry is {n, s, sec_b (when spoken), src, prev (the old Chinese, for a changed entry)}: the English
text the narrator reads, and "src", the English clipHash it stands for. scripts/fullrun.py takes the finished
work/tr-out/<batch>.zh.json, keeps "src" with the translation, and records it. Stop the recorder before export:
two processes must not write manifest/clips.jsonl at once.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import ROOT, first_section_spoken, load_json, read_jsonl  # noqa: E402

MANIFEST = ROOT / "manifest" / "clips.jsonl"
IN, OUT = ROOT / "work" / "tr-in", ROOT / "work" / "tr-out"
NEEDS = ("untranslated", "retranslate")


def recorder_running():
    pid = ROOT / "work" / "fullrun.pid"
    if pid.exists():
        try:
            os.kill(int(pid.read_text().strip()), 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    return subprocess.run(["pgrep", "-f", "scripts/(fullrun|tts_zh).py"], capture_output=True).returncode == 0


def status(_a=None):
    rows = read_jsonl(MANIFEST)
    ids = {}
    for r in rows:
        ids.setdefault(r["id"], r)
    print(f"{len(rows)} clips ({len(ids)} unique):", dict(Counter(r["status"] for r in ids.values())))
    by = {}
    for r in rows:
        by.setdefault(r["pack"], Counter())[r["status"]] += 1
    for pk, c in by.items():
        print(f"  {pk}: {dict(c)}")
    waiting = sorted(p.name for p in IN.glob("*.en.json")
                     if not (ROOT / "translations" / "zhCN" / p.name.replace(".en.json", ".json")).exists())
    if waiting:
        print("batches not taken yet:", ", ".join(waiting))


def export(a):
    if recorder_running():
        sys.exit("the recorder is running: stop it first (UPDATING.md, step 1)")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"), "prepare", "--scope", "all"],
                   check=True, cwd=ROOT)
    core = load_json(ROOT / "work" / "core.json")
    tr = {}
    for f in sorted((ROOT / "translations" / "zhCN").glob("*.json")):
        tr.update({k: v for k, v in load_json(f).items() if not k.startswith("_")})
    pending = set()   # already handed out and not back yet
    for p in IN.glob("*.en.json"):
        if not (ROOT / "translations" / "zhCN" / p.name.replace(".en.json", ".json")).exists():
            pending |= set(load_json(p))
    todo, seen = [], set()
    for r in read_jsonl(MANIFEST):
        if r["status"] in NEEDS and r["id"] not in seen and r["id"] not in pending:
            seen.add(r["id"])
            todo.append(r)
    if not todo:
        print("nothing new to translate")
        return
    stamp = time.strftime("%Y%m%d")
    start = 1 + len(list(IN.glob(f"upd-{stamp}-*.en.json")))
    IN.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for i in range(0, len(todo), a.size):
        batch = {}
        for r in todo[i:i + a.size]:
            en = core["entries"][r["id"]]
            e = {"n": en["n"], "s": en["s"]}
            if first_section_spoken(en):
                e["sec_b"] = en["sec"][0]["b"]
            e["src"] = r["en_clip_hash"]
            old = tr.get(r["id"])
            if r["status"] == "retranslate" and old:
                e["prev"] = {"n": old["n"], "s": old["s"]}
                if old.get("sec"):
                    e["prev"]["sec_b"] = old["sec"][0]["b"]
            batch[r["id"]] = e
        path = IN / f"upd-{stamp}-{start + len(made):02d}.en.json"
        path.write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
        made.append(path)
    kinds = Counter(r["status"] for r in todo)
    print(f"{len(todo)} entries to translate ({kinds['untranslated']} new, {kinds['retranslate']} changed) in "
          f"{len(made)} batches:")
    for p in made:
        print(f"  {p.relative_to(ROOT)} -> work/tr-out/{p.name.replace('.en.json', '.zh.json')}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=status)
    e = sub.add_parser("export")
    e.add_argument("--size", type=int, default=150, help="entries per batch")
    e.set_defaults(fn=export)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
