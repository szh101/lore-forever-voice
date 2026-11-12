"""Self-check the built Chinese narration packs in Lua 5.1 (lupa), as the game would load them.

  python scripts/selfcheck.py --build build --addons addons --json build/selfcheck.json

Checks: every pack loads through a fake LoreForeverPacks.Begin; toc fields (enUS, voice, female, Extends);
c[id] equals the add-on's current English clipHash; each scoped row's hash equals c[id]; the add-on's own
Voice.ScopedClip (taken from its Voice.lua) accepts every clip with English shown and returns its Chinese words;
every Audio/<stem>.mp3 exists and is an MP3; P.len for every clip; no clip id in two packs. Spoken titles,
headings and hidden passages carry the add-on's clipHash; the add-on's own Voice.Transport accepts every complete
story, whose pieces exist and whose text is Chinese.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import VOICE, clip_stem  # noqa: E402
import luaload  # noqa: E402

REQ = {"X-LoreForever-Pack": "voice", "X-LoreForever-Locale": "enUS", "X-LoreForever-Format": "1",
       "X-LoreForever-Gender": "female", "Dependencies": "LoreForever", "LoadOnDemand": "1"}

PRELUDE = """
ns = { Packs = { data = {}, recs = {} }, DB = { entries = {} }, lang = { locale = "enUS" }, readingLocale = "enUS" }
ns.Packs.Get = function(name) return ns.Packs.recs[name] end
Voice = {}
local function readingLocale() return ns.readingLocale or "enUS" end
local function sameLanguage(a, b) return (a or "enUS"):sub(1, 2) == (b or "enUS"):sub(1, 2) end
local function words(s) return type(s) == "string" and s:find("%S") ~= nil end
"""


def addon_function(voice_lua, name):
    src = Path(voice_lua).read_text(encoding="utf-8")
    m = re.search(r"\nfunction " + re.escape(name) + r"\(.*?\n end\n|\nfunction " + re.escape(name) + r"\(.*?\nend\n",
                  src, re.S)
    if not m:
        raise SystemExit(f"{name} not found in {voice_lua}")
    return m.group(0)


def local_function(voice_lua, name):
    src = Path(voice_lua).read_text(encoding="utf-8")
    m = re.search(r"\nlocal function " + re.escape(name) + r"\([^\n]*\bend\n", src)   # one line
    if not m:
        m = re.search(r"\nlocal function " + re.escape(name) + r"\(.*?\nend\n", src, re.S)
    if not m:
        raise SystemExit(f"local function {name} not found in {voice_lua}")
    return m.group(0)


TRANSPORT_PRELUDE = """
Voice.PLAYBACK_RATES = { 1 }
Voice.brokenTransport = {}
local function S() return {} end
local function readingLocale() return ns.readingLocale or "enUS" end
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build")
    ap.add_argument("--addons", default="addons")
    ap.add_argument("--json")
    a = ap.parse_args()
    build = Path(a.build)
    problems, info = [], {}
    core = luaload.load_core(a.addons)
    L = luaload.runtime()
    L.execute(PRELUDE + addon_function(Path(a.addons) / "LoreForever" / "Voice.lua", "Voice.ScopedClip")
              + addon_function(Path(a.addons) / "LoreForever" / "Voice.lua", "Voice.ClipCurrent"))
    vl = Path(a.addons) / "LoreForever" / "Voice.lua"
    L.execute(TRANSPORT_PRELUDE + local_function(vl, "finite") + local_function(vl, "transportPath")
              + local_function(vl, "dense") + addon_function(vl, "Voice.Transport"))
    g = L.globals()
    g.ns.DB.fullclips = L.table_from(core["fullclips"])
    # The entries ScopedClip needs: just that each id is in the add-on data.
    voices = sorted(p.name for p in build.iterdir() if p.is_dir() and p.name.startswith(VOICE))
    if VOICE not in voices:
        problems.append(f"{VOICE} (the base narrator) wasn't built")
    seen = {}
    for v in voices:
        P = luaload.load_pack(L, build / v)
        t = luaload.toc_fields(build / v)
        for f, want in REQ.items():
            if t.get(f) != want:
                problems.append(f"{v}: toc {f} = {t.get(f)!r}, want {want!r}")
        if v != VOICE and t.get("X-LoreForever-Extends") != VOICE:
            problems.append(f"{v}: X-LoreForever-Extends should be {VOICE}")
        if re.search(r"_[a-z]{2}[A-Z]{2}$", v):
            problems.append(f"{v}: a locale suffix would make it that language's voice (Voice.KeyOf)")
        clips, lens, scoped = P.get("clips", {}), P.get("len", {}), P.get("scopedClips", {})
        if P.get("scopedVersion") != 1:
            problems.append(f"{v}: P.scopedVersion must be 1")
        # Register the pack for the add-on's code: loaded data and its record (locale from the toc).
        lp = L.globals()._PACKS[v]
        g.ns.Packs.data[v] = lp
        g.ns.Packs.recs[v] = L.table_from({"name": v, "locale": t.get("X-LoreForever-Locale")})
        current = 0
        for k, h in clips.items():
            # The English Alliance and Horde packs both carry some stories (an orc in Ashenvale); ours follow them.
            # Fine as long as both copies are the same recording.
            if k in seen and seen[k][1] != h:
                problems.append(f"{v}: {k} also in {seen[k][0]} with a different recording")
            seen.setdefault(k, (v, h))
            if "#" in k:   # a spoken title, heading or hidden passage (scripts/stories.py): a plain clip
                quest = re.match(r"^quest:\d+#(detail|progress|complete)$", k)
                if (core["questClip"] if quest else core["clipHash"]).get(k) != h:
                    problems.append(f"{v}: {k} hash isn't the add-on's {'questClip' if quest else 'clipHash'}")
                mp3 = build / v / "Audio" / (clip_stem(k) + ".mp3")
                if not mp3.is_file():
                    problems.append(f"{v}: missing {mp3.relative_to(build)}")
                if not isinstance(lens.get(k), (int, float)) or lens.get(k) <= 0:
                    problems.append(f"{v}: no P.len for {k}")
                continue
            if k not in core["entries"]:
                problems.append(f"{v}: {k} is not an entry in the add-on data")
                continue
            g.ns.DB.entries[k] = L.table_from({"n": core["entries"][k]["n"]})
            if core["clipHash"].get(k) == h:
                current += 1
            sr = scoped.get(k)
            if not sr or sr.get("hash") != h:
                problems.append(f"{v}: {k} scoped row missing or its hash differs from c[id]")
            ok = g.Voice.ScopedClip(k, v)
            row, text, title = ok if isinstance(ok, tuple) else (ok, None, None)
            if row is None or not text:
                problems.append(f"{v}: Voice.ScopedClip refuses {k}")
            elif not re.search(r"[一-鿿]", text):
                problems.append(f"{v}: {k} words aren't Chinese")
            if not g.Voice.ClipCurrent(k, v, core["clipHash"].get(k)):
                problems.append(f"{v}: Voice.ClipCurrent false for {k}")
            mp3 = build / v / "Audio" / (clip_stem(k) + ".mp3")
            if not mp3.is_file():
                problems.append(f"{v}: missing {mp3.relative_to(build)}")
            else:
                head = mp3.read_bytes()[:3]
                if head != b"ID3" and head[:2] not in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
                    problems.append(f"{v}: {mp3.name} is not an MP3")
            if not isinstance(lens.get(k), (int, float)) or lens.get(k) <= 0:
                problems.append(f"{v}: no P.len for {k}")
        transport = P.get("transport", {})
        for k, row in transport.items():
            got = g.Voice.Transport(k, v, True)
            if got is None:
                problems.append(f"{v}: Voice.Transport refuses the complete story {k}")
                continue
            for part in row.get("1", []):
                if not (build / v / part["file"]).is_file():
                    problems.append(f"{v}: {k} missing {part['file']}")
            if not re.search(r"[一-鿿]", row.get("text", "")):
                problems.append(f"{v}: {k} complete story text isn't Chinese")
        info[v] = {"clips": len(clips), "complete_stories": len(transport), "len": len(lens), "scoped": len(scoped),
                   "current_with_english": current, "sample": t.get("X-LoreForever-Sample"),
                   "extends": t.get("X-LoreForever-Extends"), "title": t.get("Title")}
    result = {"ok": not problems, "problems": problems, "packs": info}
    if a.json:
        Path(a.json).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=1))
    print("PROBLEMS:" if problems else "ALL CHECKS PASSED", *problems[:50], sep="\n  ")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
