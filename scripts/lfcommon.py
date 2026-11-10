"""Shared helpers for building the Chinese narration packs of Lore Forever.

The packs are a separate narrator, LoreForever_Voice_ChineseFemale (+ _Alliance, _MorePeople ... mirroring the English
female packs), with X-LoreForever-Locale: enUS: it plays while Lore Forever shows English text (Voice.Unusable only
lets packs in the reading language play). Each recording is a community-voice "scoped clip" (Voice.ScopedClip) that
carries the Chinese words it reads, so subtitles show them, and it keeps playing when the English text is reworded.

Hash rules (reverse-engineered from Lore Forever 1.4.0 data and verified against the shipped packs, see REPORT.md):
  clipHash[key]  = sha1(overview_text(entry)).hexdigest()[:6]
  overview_text  = whitespace-collapsed  n + ". " + s [+ " " + sec[1].b  when sec[1] exists and its sp == 0]
  fullclips[key] = sha1(full story text)[:6]   (not used by the zhCN packs: they record the overview only, like frFR)
  Lang.Fingerprint(e) = byte lengths of the ENGLISH entry (Lang.lua): "#n,#s,#t.#b.sp,...,#q.#a.sp,..."
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_VERSION = "1.4.0"
LOCALE = "zhCN"          # the language spoken (the packs themselves are enUS: they play over English text)
VOICE = "LoreForever_Voice_ChineseFemale"

# English female packs and their zhCN counterparts. Extends follows LoreForever_Voice_Female_MorePeople_frFR.
PACKS = ["Female", "Alliance", "Horde", "MoreItems", "MorePeople", "MorePlaces",
         "Quests", "Quests2", "Quests3", "MoreQuests1", "MoreQuests2", "MoreQuests3"]


def en_pack(pk):
    return "LoreForever_Voice_Female" + ("" if pk == "Female" else "_" + pk)


def zh_pack(pk):
    return VOICE + ("" if pk == "Female" else "_" + pk)


def sha6(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]


def ws(text):
    return re.sub(r"\s+", " ", text).strip()


def first_section_spoken(en):
    """Whether the overview includes section 1: it exists and the ENGLISH entry doesn't flag it as a spoiler."""
    secs = en.get("sec") or []
    return bool(secs) and (secs[0].get("sp") or 0) == 0


def overview_text(e, en=None):
    """The text an entry's own clip reads (what clipHash is computed over). en: the English entry (spoiler flags)."""
    secs = e.get("sec") or []
    t = e["n"] + ". " + e["s"]
    if secs and first_section_spoken(en or e):
        t += " " + secs[0]["b"]
    return ws(t)


def spoken_zh(e, en):
    """What the zhCN narrator says: same parts as overview_text, joined the Chinese way."""
    secs = e.get("sec") or []
    parts = [e["n"].strip() + "。", e["s"].strip()]
    if secs and first_section_spoken(en):
        parts.append(secs[0]["b"].strip())
    t = "".join(p if re.search(r"[。！？…”」]$", p) else p + "。" for p in parts[:-1]) + parts[-1]
    return ws(t)


def fingerprint(e):
    """Lang.Fingerprint over the English entry (lengths in UTF-8 bytes, as Lua's # gives)."""
    b = lambda s: len((s or "").encode("utf-8"))
    p = [str(b(e.get("n"))), str(b(e.get("s")))]
    for s in e.get("sec") or []:
        p.append(f"{b(s.get('t'))}.{b(s.get('b'))}.{s.get('sp') or 0}")
    for f in e.get("faq") or []:
        if not f.get("add"):
            p.append(f"{b(f.get('q'))}.{b(f.get('a'))}.{f.get('sp') or 0}")
    return ",".join(p)


def lua_str(s):
    """A Lua 5.1 double-quoted string literal (UTF-8 passes through as bytes)."""
    out = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return '"' + out + '"'


def lua_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, list):
        return "{" + ",".join(lua_val(x) for x in v) + "}"
    if isinstance(v, dict):
        items = []
        for k, x in v.items():
            key = k if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) else "[" + lua_str(k) + "]"
            items.append(f"{key}={lua_val(x)}")
        return "{" + ",".join(items) + "}"
    raise TypeError(type(v))


def clip_stem(clip_id):
    """Voice.ClipPath: zone:stormwind -> zone_stormwind (# -> __, other non [%w-_] -> _)."""
    return re.sub(r"[^0-9A-Za-z\-_]", "_", clip_id.replace("#", "__"))


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def dump_json(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")   # write then rename, so a reader never sees half a file
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(p)
