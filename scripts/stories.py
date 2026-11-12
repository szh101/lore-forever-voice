"""Complete stories: the rest of each story after its overview, its spoken headings and title, and hidden passages.

  python scripts/stories.py export [--batches 20]   work/tr-story-in/story-NN.en.json (what needs translating)
  python scripts/stories.py take                    finished work/tr-story-out/story-NN.zh.json -> translations/
  python scripts/stories.py prepare                 translations + work/*.json -> manifest/stories.jsonl
  python scripts/stories.py split                   cut each recorded overview where its section 1 starts

What the English female packs play for a story (Voice.Play, Voice.Transport, UI.EntryTarget):
  <key>            the complete story when the pack has one in Transport.lua (fullHash = our fullclips[key]): its
                   name, summary and every section that isn't a spoiler, in pieces (chain); the piece where section n
                   starts is marked head = n, and a full listen starts at section 1. Else the overview.
  <key>#title      the story's name, spoken just before a full listen.
  <key>#head<n>    section n's heading, spoken where that section starts.
  <key>#section<n> a hidden (spoiler) section the player has reached, played after the story.

Ours: the complete story's first piece is the overview's own recording up to section 1 (cut where section 1 starts,
`split`, timed by a local forced aligner), then section 1 (the rest of that recording), then one recording per further section. A manifest row per
recording, like manifest/clips.jsonl, so scripts/tts_zh.py records them:
  kind piece   id <key>@sec<n>   a section of a complete story (n >= 2, or 1 when the overview has no section)
  kind head    id <key>#head<n>  hash: the English clipHash of that id
  kind title   id <key>#title
  kind passage id <key>#section<n>
plus the cut overviews (kind intro / sec1, recorded = derived from the overview's audio by `split`).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import PACKS, ROOT, clip_stem, en_pack, load_json, read_jsonl, write_jsonl, zh_pack  # noqa: E402

IN, OUT = ROOT / "work" / "tr-story-in", ROOT / "work" / "tr-story-out"
TR = ROOT / "translations" / "zhCN" / "stories"
MANIFEST = ROOT / "manifest" / "stories.jsonl"
OVERVIEWS = ROOT / "manifest" / "clips.jsonl"
KEEP = ("audio", "duration", "status", "chars_per_sec", "recorded_text_sha")


def spoiler(sec):
    return str(sec.get("sp") or 0) != "0"


def lore_packs(packs):
    """{english pack: zh pack} for the lore packs (quest dialogue packs are separate)."""
    return {en_pack(pk): zh_pack(pk) for pk in PACKS if en_pack(pk) in packs and not pk.startswith("Quests")}


def wanted(core, packs, overview_ids):
    """What the English female lore packs have that ours should: {(zh pack, kind, key, n)}."""
    E, out = core["entries"], set()
    for ep, zp in lore_packs(packs).items():
        p = packs[ep]
        for k, row in (p.get("transport") or {}).items():
            if k in overview_ids and row.get("fullHash") and core["fullclips"].get(k) == row["fullHash"]:
                for n, sec in enumerate(E[k].get("sec") or [], 1):
                    if not spoiler(sec):
                        out.add((zp, "piece", k, n))
        for cid in p.get("clips", {}):
            m = re.match(r"^(.*)#(head|section)(\d+)$", cid)
            if cid.endswith("#title") and cid[:-6] in E:
                out.add((zp, "title", cid[:-6], 0))
            elif m and m.group(1) in E and int(m.group(3)) <= len(E[m.group(1)].get("sec") or []):
                out.add((zp, "head" if m.group(2) == "head" else "passage", m.group(1), int(m.group(3))))
    return out


def load():
    core = load_json(ROOT / "work" / "core.json")
    packs = load_json(ROOT / "work" / "packs.json")
    ov = {}
    for r in read_jsonl(OVERVIEWS):
        ov.setdefault(r["id"], r)
    return core, packs, ov


def translations():
    out = {}
    for f in sorted(TR.glob("*.json")):
        for k, v in load_json(f).items():
            if not k.startswith("_"):
                out.setdefault(k, {"sec": {}})
                out[k]["src"] = v.get("src")
                for s in v["sec"]:
                    out[k]["sec"].setdefault(str(s["i"]), {}).update({x: s[x] for x in ("t", "b") if x in s})
    return out


def overview_sec1(ov_row):
    """Whether the overview recording reads section 1 (then that section needs no new translation)."""
    return bool(ov_row and ov_row.get("zh_section"))


def export(a):
    core, packs, ov = load()
    E, tr = core["entries"], translations()
    need = {}
    for zp, kind, k, n in wanted(core, packs, set(ov)):
        if kind == "title":
            continue   # the name: translated with the overview
        sec = E[k]["sec"][n - 1]
        have = tr.get(k, {}).get("sec", {}).get(str(n), {})
        fresh = tr.get(k, {}).get("src") == core["fullclips"].get(k)
        item = need.setdefault(k, {}).setdefault(n, {})
        if kind == "head" and not (fresh and have.get("t")):
            item["t"] = sec["t"]
        if kind in ("piece", "passage") and not (n == 1 and kind == "piece" and overview_sec1(ov.get(k))) \
                and not (fresh and have.get("b")):
            item["b"] = sec["b"]
    need = {k: {n: v for n, v in secs.items() if v} for k, secs in need.items()}
    need = {k: v for k, v in need.items() if v}
    if not need:
        print("nothing to translate")
        return
    IN.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    keys = sorted(need)
    size = lambda k: sum(len(v.get("t", "")) + len(v.get("b", "")) for v in need[k].values())
    total = sum(size(k) for k in keys)
    per, batch, made, n = total / a.batches, {}, [], len(list(IN.glob("story-*.en.json")))

    def flush():
        nonlocal batch
        if batch:
            p = IN / f"story-{n + len(made) + 1:02d}.en.json"
            p.write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding="utf-8")
            made.append(p)
            batch = {}
    acc = 0
    for k in keys:
        o = ov.get(k, {})
        batch[k] = {"src": core["fullclips"].get(k), "name_zh": o.get("zh_name"), "summary_zh": o.get("zh_summary"),
                    "sec": [{"i": i, **v} for i, v in sorted(need[k].items())]}
        acc += size(k)
        if acc >= per * (len(made) + 1):
            flush()
    flush()
    print(f"{len(keys)} stories, {total:,} English characters, {len(made)} batches in {IN.relative_to(ROOT)}")


def take(_a=None):
    TR.mkdir(parents=True, exist_ok=True)
    done = 0
    for src in sorted(IN.glob("story-*.en.json")):
        name = src.name.split(".")[0]
        zh, dest = OUT / f"{name}.zh.json", TR / f"{name}.json"
        if dest.exists():
            done += 1
            continue
        if not zh.exists():
            continue
        try:
            en, t = load_json(src), load_json(zh)
        except json.JSONDecodeError:
            continue
        ok = set(k for k in t if not k.startswith("_")) == set(en)
        for k, v in en.items():
            if not ok:
                break
            got = {s.get("i"): s for s in (t[k].get("sec") or [])}
            for s in v["sec"]:
                g = got.get(s["i"])
                if not g or any(bool(g.get(x, "").strip()) != (x in s) for x in ("t", "b")):
                    ok = False
                    break
        if not ok:
            print(f"{name}: not finished or not matching its input", flush=True)
            continue
        out = {k: {"src": en[k]["src"], "sec": [{x: s[x] for x in ("i", "t", "b") if x in s}
                                                for s in t[k]["sec"]]} for k in en}
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(ROOT / "glossary" / "new-terms-full.tsv", "a", encoding="utf-8") as f:
            for term in t.get("_new_terms", []):
                f.write("\t".join(map(str, term)) + f"\t{name}\n")
        print(f"took {name}: {len(out)} stories", flush=True)
        done += 1
    total = len(list(IN.glob("story-*.en.json")))
    print(f"story batches {done}/{total}")
    return done, total


def zh_text(s):
    s = s.strip()
    return s if re.search(r"[。！？…”」]$", s) else s + "。"


def prepare(_a=None):
    core, packs, ov = load()
    E, CH, tr = core["entries"], core["clipHash"], translations()
    old = {(r["pack"], r["id"]): r for r in read_jsonl(MANIFEST)}
    rows = []
    for zp, kind, k, n in sorted(wanted(core, packs, set(ov))):
        o, t = ov.get(k, {}), tr.get(k, {})
        sec = t.get("sec", {}).get(str(n), {})
        stem = clip_stem(k)
        row = {"pack": zp, "kind": kind, "key": k, "n": n, "status": "untranslated"}
        if kind == "piece":
            if n == 1 and overview_sec1(o):
                continue   # section 1 is the overview's second half (split)
            row.update(id=f"{k}@sec{n}", stem=f"Transport/{stem}/sec{n:02d}", text=sec.get("b"))
        elif kind == "head":
            row.update(id=f"{k}#head{n}", stem=clip_stem(f"{k}#head{n}"), text=sec.get("t"), hash=CH.get(f"{k}#head{n}"))
        elif kind == "title":
            row.update(id=f"{k}#title", stem=clip_stem(f"{k}#title"), text=o.get("zh_name"), hash=CH.get(f"{k}#title"))
        else:
            row.update(id=f"{k}#section{n}", stem=clip_stem(f"{k}#section{n}"), text=sec.get("b"),
                       hash=CH.get(f"{k}#section{n}"))
        if kind in ("head", "title", "passage") and not row.get("hash"):
            continue   # our data has no clip there to be heard
        if row["text"] and (kind == "title" or t.get("src") == core["fullclips"].get(k)):
            row["zh_text"] = zh_text(row["text"]) if kind != "title" else row["text"].strip()
            row["status"] = "pending"
            prev = old.get((zp, row["id"]))
            if prev and prev.get("status") in ("recorded", "check") and prev.get("zh_text") == row["zh_text"]:
                row.update({f: prev[f] for f in KEEP if f in prev})
        elif row["text"]:
            row["status"] = "retranslate"
        rows.append(row)
    write_jsonl(MANIFEST, rows)
    by = {}
    for r in rows:
        by.setdefault(r["kind"], {}).setdefault(r["status"], 0)
        by[r["kind"]][r["status"]] += 1
    print(f"stories manifest: {len(rows)} recordings {by}")


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def duration_of(path):
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    h, m, sec = re.findall(r"time=(\d+):(\d+):([\d.]+)", out.stderr)[-1]
    return round(int(h) * 3600 + int(m) * 60 + float(sec), 3)


ALIGNER = Path.home() / "Workspace/voice-studio/.runtime/data/models/qwen3-forcedaligner-0.6b-bf16"


def split(a):
    """Cut each recorded overview that reads section 1 where section 1 starts: intro (name, summary) and sec1.

    Qwen3-ForcedAligner (mlx-audio, local) times every character of the text the overview read; the cut goes midway
    between the summary's last character and section 1's first."""
    from mlx_audio.stt.utils import load_model
    model = load_model(str(a.aligner))
    audio = Path(a.audio)
    path = ROOT / "work" / "overview-cuts.json"
    cuts = load_json(path) if path.exists() else {}
    made = 0
    for r in read_jsonl(OVERVIEWS):
        if r.get("status") != "recorded" or not r.get("zh_section") or r["id"] in cuts \
                and cuts[r["id"]].get("sha") == r.get("recorded_text_sha"):
            continue
        mp3 = audio / r["audio"]
        head = r["zh_text"][:r["zh_text"].index(r["zh_section"].strip()[:8])] if r["zh_section"].strip()[:8] \
            in r["zh_text"] else None
        cut = {"sha": r.get("recorded_text_sha"), "at": None}
        if head:
            words, _ = model.aligner_processor.encode_timestamp(head, "Chinese")
            items = list(model.generate(str(mp3), r["zh_text"], language="Chinese").items)
            n = len(words)
            if 0 < n < len(items):
                at = (items[n - 1].end_time + items[n].start_time) / 2
                if 1.0 < at < r["duration"] - 1.0:
                    cut["at"] = round(at, 3)
        if cut["at"]:
            base = audio / "mp3" / r["pack"] / "Transport" / clip_stem(r["id"])
            base.mkdir(parents=True, exist_ok=True)
            for name, args in (("intro", ["-t", f"{cut['at']:.3f}"]), ("sec01", ["-ss", f"{cut['at']:.3f}"])):
                subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3)] + args +
                               ["-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k",
                                str(base / f"{name}.mp3")], check=True)
            cut["intro"] = str((base / "intro.mp3").relative_to(audio))
            cut["sec1"] = str((base / "sec01.mp3").relative_to(audio))
            cut["intro_duration"] = duration_of(base / "intro.mp3")
            cut["sec1_duration"] = duration_of(base / "sec01.mp3")
        cuts[r["id"]] = cut
        made += 1
        if made % 100 == 0:
            path.write_text(json.dumps(cuts))
            print(f"cut {made}", flush=True)
        if a.limit and made >= a.limit:
            break
    path.write_text(json.dumps(cuts))
    ok = sum(1 for c in cuts.values() if c.get("at"))
    print(f"overviews cut: {ok} of {len(cuts)} (the rest play whole, without a section 1 mark)")
    print(f"cut this run: {made}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--batches", type=int, default=20)
    e.set_defaults(fn=export)
    sub.add_parser("take").set_defaults(fn=take)
    sub.add_parser("prepare").set_defaults(fn=prepare)
    s = sub.add_parser("split")
    s.add_argument("--audio", default="work/audio")
    s.add_argument("--aligner", default=str(ALIGNER))
    s.add_argument("--limit", type=int)
    s.set_defaults(fn=split)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
