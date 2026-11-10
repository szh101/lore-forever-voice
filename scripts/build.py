"""Build the Chinese narration packs (a separate narrator that reads in Chinese while Lore Forever shows English).

  python scripts/build.py prepare [--scope pilot|all]   translations/ + work/*.json -> manifest/clips.jsonl
  python scripts/build.py packs --audio work/audio --out build
                                                        manifest -> build/<add-on folders>

translations/zhCN/*.json: {entry key: {n, s, sec: [{t, b}], ...}}. Only what an overview recording reads is used:
the name, the summary and, when the English entry reads it, section 1's body (lfcommon.overview_text).
A row of manifest/clips.jsonl per clip:
  id, pack, en_pack, en_clip_hash (the English clipHash the recording stands for), en_fp, zh_name, zh_summary,
  zh_section (or null), zh_text (what is spoken), stem, audio, duration, status
A row whose English changes (en_fp) goes to "retranslate"; one whose Chinese text changes goes back to "pending".
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import (CORE_VERSION, LOCALE, PACKS, ROOT, VOICE, clip_stem, dump_json, en_pack,  # noqa: E402
                      first_section_spoken, fingerprint, load_json, lua_str, lua_val, read_jsonl, spoken_zh,
                      write_jsonl, zh_pack)

TRANSLATIONS = ROOT / "translations" / LOCALE
MANIFEST = ROOT / "manifest" / "clips.jsonl"
SCOPE = ROOT / "manifest" / "scope.json"
KEEP = ("audio", "duration", "status", "chars_per_sec", "recorded_text_sha")


def translations():
    out = {}
    for f in sorted(TRANSLATIONS.glob("*.json")):
        for k, v in load_json(f).items():
            if not k.startswith("_"):
                out[k] = v
    return out


def scope_keys(core, packs, scope):
    """{english pack key: [clip ids]}. pilot: manifest/scope.json; all: every English female overview clip."""
    if scope == "pilot":
        return load_json(SCOPE)
    out = {}
    for pk in PACKS:
        clips = packs.get(en_pack(pk), {}).get("clips", {})
        out[pk] = sorted(k for k in clips if "#" not in k and k in core["entries"])
    return out


def prepare(a):
    core = load_json(ROOT / "work" / "core.json")
    packs = load_json(ROOT / "work" / "packs.json")
    tr = translations()
    old = {r["id"]: r for r in read_jsonl(MANIFEST)}
    rows, missing = [], []
    for pk, ids in scope_keys(core, packs, a.scope).items():
        for k in ids:
            en = core["entries"][k]
            row = {"id": k, "pack": zh_pack(pk), "en_pack": en_pack(pk), "en_clip_hash": core["clipHash"].get(k),
                   "en_fp": fingerprint(en), "stem": clip_stem(k), "status": "untranslated"}
            t = tr.get(k)
            if t:
                sec = t["sec"][0]["b"] if t.get("sec") and first_section_spoken(en) else None
                row.update(zh_name=t["n"], zh_summary=t["s"], zh_section=sec, zh_text=spoken_zh(t, en), status="pending")
                prev = old.get(k)
                if prev and prev.get("en_fp") and prev["en_fp"] != row["en_fp"]:
                    row["status"] = "retranslate"   # the English moved on since this translation was made
                elif prev and prev.get("status") in ("recorded", "check") and prev.get("zh_text") == row["zh_text"]:
                    row.update({f: prev[f] for f in KEEP if f in prev})
            else:
                missing.append(k)
            rows.append(row)
    write_jsonl(MANIFEST, rows)
    by = {}
    for r in rows:
        by[r["status"]] = by.get(r["status"], 0) + 1
    print(f"manifest: {len(rows)} clips {by}; untranslated: {len(missing)}")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


CREDITS = """{title}
{line}

Chinese (Mandarin) narration for the World of Warcraft add-on Lore Forever (by mikeliudev, CurseForge project
1715510), read over its English text. Made by szh101 for personal use; not an official Lore Forever pack.

License
-------
The narration scripts are Simplified Chinese translations of Lore Forever's lore text, which it adapts from articles
on the Warcraft Wiki (https://warcraft.wiki.gg, CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/) and
some from Wowpedia (https://wowpedia.fandom.com, CC BY-SA 3.0). The translations are shared under the same license.
The voice is an AI voice owned by the pack's maker, licensed for this narration only: do not reuse the recordings.

World of Warcraft
-----------------
World of Warcraft and Warcraft are trademarks of Blizzard Entertainment, Inc.
Lore Forever is a fan-made add-on and is not affiliated with or endorsed by Blizzard.
"""

TITLES = {"Female": "Lore Forever Chinese female narrator"}


def pack_title(pk, en_toc):
    if pk in TITLES:
        return TITLES[pk]
    # "Lore Forever more people (female narrator)" -> "Lore Forever more people (Chinese female narrator)"
    t = en_toc.get("Title", en_pack(pk))
    return t.replace("female narrator", "Chinese female narrator") if "female narrator" in t else t + " (Chinese)"


def build_voice(out, rows, audio, tocs):
    built = []
    by_pack = {}
    for r in rows:
        if r.get("status") == "recorded":
            by_pack.setdefault(r["pack"], []).append(r)
    for pack, rs in sorted(by_pack.items()):
        d = out / pack
        shutil.rmtree(d, ignore_errors=True)
        pk = "Female" if pack == VOICE else pack[len(VOICE) + 1:]
        en_toc = tocs.get(en_pack(pk), {})
        lines = ["## Interface: 16001", f"## Title: {pack_title(pk, en_toc)}",
                 "## Notes: Chinese narration for Lore Forever, read over its English text.",
                 "## Author: szh101", f"## Version: {CORE_VERSION}", "## Dependencies: LoreForever",
                 "## LoadOnDemand: 1", "## X-LoreForever-Pack: voice", "## X-LoreForever-Locale: enUS",
                 "## X-LoreForever-Format: 1", "## X-LoreForever-Gender: female",
                 "## X-LoreForever-Credit: Chinese narration: szh101's documentary voice (AI)"]
        if pack == VOICE:
            sample = en_toc.get("X-LoreForever-Sample")
            if sample and any(r["id"] == sample for r in rs):
                lines.append(f"## X-LoreForever-Sample: {sample}")
        else:
            lines.append(f"## X-LoreForever-Extends: {VOICE}")
        write(d / f"{pack}.toc", "\n".join(lines + ["Clips.lua", ""]))
        c = ("-- Generated by lore-forever-voice/scripts/build.py - do not edit by hand.\n"
             "-- Chinese recordings of Lore Forever's English entries. Each carries the words it reads (scopedClips,\n"
             "-- see Voice.ScopedClip): they play with those words as subtitles, whatever the English says now.\n"
             "local name = ...\nlocal P = LoreForeverPacks and LoreForeverPacks.Begin(name)\n"
             "if not P then return end\nlocal c = P.clips\n")
        sc = "P.scopedVersion = 1\nP.scopedClips = P.scopedClips or {}\nlocal s = P.scopedClips\n"
        ln = "local l = {}\nP.len = l\n"
        for r in sorted(rs, key=lambda r: r["id"]):
            dst = d / "Audio" / (r["stem"] + ".mp3")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(audio) / r["audio"], dst)
            h = r["en_clip_hash"]
            c += f"c[{lua_str(r['id'])}] = {lua_str(h)}\n"
            row = {"hash": h, "sourceHash": h, "scope": "overview-body", "name": r["zh_name"], "summary": r["zh_summary"]}
            if r.get("zh_section"):
                row["section"] = r["zh_section"]
                row["sectionIndex"] = 1
            sc += f"s[{lua_str(r['id'])}] = {lua_val(row)}\n"
            ln += f"l[{lua_str(r['id'])}] = {max(1, round(r['duration'] * 10))}\n"
        write(d / "Clips.lua", c + sc + ln)
        write(d / "CREDITS.txt", CREDITS.format(title=pack_title(pk, en_toc), line="=" * 60))
        built.append(pack)
    return built


def packs_cmd(a):
    tocs = load_json(ROOT / "work" / "tocs.json")
    rows = read_jsonl(MANIFEST)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():   # nothing left over from an earlier layout
        if old.is_dir():
            shutil.rmtree(old)
    names = build_voice(out, rows, a.audio, tocs)
    dump_json(out / "built.json", names)
    print("built:", ", ".join(names))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--scope", choices=["pilot", "all"], default="pilot")
    p.set_defaults(fn=prepare)
    p = sub.add_parser("packs")
    p.add_argument("--audio", default=str(ROOT / "work" / "audio"))
    p.add_argument("--out", default=str(ROOT / "build"))
    p.set_defaults(fn=packs_cmd)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
