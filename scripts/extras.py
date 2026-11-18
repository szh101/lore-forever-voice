"""Quest giver dialogue, quest recaps and book pages: the English female packs' recordings that aren't stories.

  python scripts/extras.py export [--chars 85000]   work/tr-extra-in/<kind>-NN.en.json (what needs translating)
  python scripts/extras.py take                     finished work/tr-extra-out/<name>.zh.json -> translations/
  python scripts/extras.py prepare                  translations -> manifest/extras.jsonl (scripts/tts_zh.py)

What plays (Voice.lua; REPORT.md "Complete stories, quests, recaps and books"):
  quest:<id>#detail|progress|complete  a quest giver's page; the pack's hash must equal the add-on's questClip[id],
                                       and the page plays when the quest window shows that text
  recap:<id>#before|mid|end            a storyline's recap; hash = clipHash[id] (the add-on has the English text)
  booktext:<title>#<page>              a book, letter or plaque page; hash = clipHash[id]
Each is a plain clip (Audio/<stem>.mp3, P.clips, P.len), the English hash copied: it plays while the add-on's
English is the one it was translated from, and the subtitles show the English, as the text does.

The English of quest pages and book pages isn't in the add-on (the game shows it). work/sources/ has it from the
cmangos classic-db dump (quests.json, books.json; scripts in REPORT.md); a page counts as verified when its text
gives the add-on's own fingerprint (quests: Voice.QuestFingerprints) or hash (books: sha1 of the page). WoW
Forever's own quests (ids above 30000) aren't in that dump.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import ROOT, clip_stem, en_pack, load_json, read_jsonl, write_jsonl, zh_pack, PACKS  # noqa: E402

IN, OUT = ROOT / "work" / "tr-extra-in", ROOT / "work" / "tr-extra-out"
TR = ROOT / "translations" / "zhCN" / "extras"
MANIFEST = ROOT / "manifest" / "extras.jsonl"
SRC = ROOT / "work" / "sources"
KEEP = ("audio", "duration", "status", "chars_per_sec", "recorded_text_sha")
PART = {"detail": 1, "progress": 2, "complete": 3}


def djb2(s):
    h = 5381
    for ch in re.sub(r"[^0-9a-z]", "", s):
        h = (h * 33 + ord(ch)) % 4294967296
    return "%08x" % h


def quest_fps(text):
    """The add-on's fingerprints of a page as the game would show it ($N name, $C class, $R race taken out)."""
    out = set()
    for g in (1, 2):
        x = re.sub(r"\$[gG]\s*([^:;]*):([^;]*);", lambda m: m.group(g), text or "")
        x = re.sub(r"\$[bB]", " ", x)
        out.add(djb2(re.sub(r"\$[nNcCrR]", "", x).lower()))
    return out


def ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def wanted():
    """{clip id: (zh pack, kind, hash, english text or None, verified, context)} for every English female clip."""
    core = load_json(ROOT / "work" / "core.json")
    extra = load_json(ROOT / "work" / "core-extra.json")
    packs = load_json(ROOT / "work" / "packs.json")
    quests = load_json(SRC / "quests.json") if (SRC / "quests.json").exists() else {}
    books = load_json(SRC / "books.json") if (SRC / "books.json").exists() else {}
    recaps = {}
    for sid, r in extra["recaps"].items():
        for part in ("before", "mid", "end"):
            if part in r:
                for key in (f"recap:{sid}#{part}", f"recap:{r['k']}#{part}"):
                    recaps[key] = r[part]["t"]
    QV, QC, CH = core["questVoice"], extra["questClip"], core["clipHash"]
    out = {}
    for pk in PACKS:
        p = packs.get(en_pack(pk))
        if not p:
            continue
        for cid in p["clips"]:
            m = re.match(r"^quest:(\d+)#(detail|progress|complete)$", cid)
            if m:
                qid, part = m.groups()
                src = quests.get(qid) or {}
                row = QV.get(qid)
                if row and row[0] != qid:
                    src = quests.get(str(row[0])) or src
                text = src.get(part)
                text = text if text and text.strip() and text.strip().upper() != "NULL" else None   # (SQL NULL, any case)
                ok = bool(text and row and quest_fps(text) & set((row[PART[part]] or "").split()))
                out[cid] = (zh_pack(pk), "quest", QC.get(cid), text, ok, src.get("title"))
            elif cid.startswith("recap:"):
                out[cid] = (zh_pack(pk), "recap", CH.get(cid), recaps.get(cid), cid in recaps, None)
            elif cid.startswith("booktext:"):
                text = books.get(cid)
                ok = bool(text and hashlib.sha1(ws(text).encode()).hexdigest()[:6] == CH.get(cid))
                out[cid] = (zh_pack(pk), "book", CH.get(cid), text, ok, cid[9:].rsplit("#", 1)[0])
    return out


def translations():
    out = {}
    for f in sorted(TR.glob("*.json")):
        out.update({k: v for k, v in load_json(f).items() if not k.startswith("_")})
    return out


def export(a):
    tr = translations()
    pending = set()
    for p in IN.glob("*.en.json"):
        if not (TR / p.name.replace(".en.json", ".json")).exists():
            pending |= set(load_json(p))
    todo = {}
    for cid, (zp, kind, h, text, ok, ctx) in sorted(wanted().items()):
        if not text or cid in pending or (cid in tr and tr[cid].get("src") == h):
            continue
        todo.setdefault(kind, []).append((cid, {"en": text, "context": ctx, "src": h, "verified": ok}))
    IN.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, items in todo.items():
        n = len(list(IN.glob(f"{kind}-*.en.json")))
        batch, size, made = {}, 0, []
        for cid, item in items:
            batch[cid] = item
            size += len(item["en"])
            if size >= a.chars:
                made.append(batch)
                batch, size = {}, 0
        if batch:
            made.append(batch)
        for i, b in enumerate(made, n + 1):
            (IN / f"{kind}-{i:02d}.en.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{kind}: {len(items)} pages, {sum(len(x['en']) for _, x in items):,} English characters, "
              f"{len(made)} batches")


def take(_a=None):
    TR.mkdir(parents=True, exist_ok=True)
    done = 0
    srcs = sorted(IN.glob("*.en.json"))
    for src in srcs:
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
        if set(k for k in t if not k.startswith("_")) != set(en) or not all(
                isinstance(t[k], dict) and str(t[k].get("zh", "")).strip() for k in en):
            print(f"{name}: not finished or not matching its input", flush=True)
            continue
        out = {k: {"zh": t[k]["zh"].strip(), "src": en[k]["src"]} for k in en}
        dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        with open(ROOT / "glossary" / "new-terms-full.tsv", "a", encoding="utf-8") as f:
            for term in t.get("_new_terms", []):
                f.write("\t".join(map(str, term)) + f"\t{name}\n")
        print(f"took {name}: {len(out)} pages", flush=True)
        done += 1
    print(f"extra batches {done}/{len(srcs)}")
    return done, len(srcs)


def prepare(_a=None):
    tr = translations()
    old = {(r["pack"], r["id"]): r for r in read_jsonl(MANIFEST)}
    rows = []
    for cid, (zp, kind, h, text, ok, ctx) in sorted(wanted().items()):
        if not h:
            continue
        row = {"id": cid, "pack": zp, "kind": kind, "stem": clip_stem(cid), "hash": h, "verified": ok,
               "status": "no source" if not text else "untranslated"}
        t = tr.get(cid) if text else None   # (a page with no English is never voiced)
        if t and t.get("src") == h:
            row["zh_text"] = t["zh"]
            row["status"] = "pending"
            prev = old.get((zp, cid))
            if prev and prev.get("status") in ("recorded", "check") and prev.get("zh_text") == row["zh_text"]:
                row.update({f: prev[f] for f in KEEP if f in prev})
        elif t:
            row["status"] = "retranslate"
        rows.append(row)
    write_jsonl(MANIFEST, rows)
    by = {}
    for r in rows:
        by.setdefault(r["kind"], {}).setdefault(r["status"], 0)
        by[r["kind"]][r["status"]] += 1
    print(f"extras manifest: {len(rows)} recordings {by}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--chars", type=int, default=85000)
    e.set_defaults(fn=export)
    sub.add_parser("take").set_defaults(fn=take)
    sub.add_parser("prepare").set_defaults(fn=prepare)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
