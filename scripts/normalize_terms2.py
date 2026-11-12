"""Make proper nouns consistent across the complete-story and quest/recap/book translations (second round).

  python scripts/normalize_terms2.py work/terms-round2.json work/terms-canon-3.tsv

terms-round2.json: {"fixed": {en: zh}, "variants": {en: [every rendering seen]}} (the glossary's or the first run's
name where there was one); terms-canon-3.tsv: en<TAB>zh<TAB>status for the rest. In each translated entry whose
English names the thing, every other rendering of it becomes the chosen one. Names chosen for anything the entry
names are shielded first, so one replacement can't eat into another name. Edits translations/zhCN/stories/*.json
and translations/zhCN/extras/*.json in place and adds the names to glossary/zhCN.tsv.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(round2, canon_tsv):
    r2 = load(round2)
    canon = dict(r2["fixed"])
    status = {}
    for line in Path(canon_tsv).read_text(encoding="utf-8").splitlines()[1:]:
        en, zh, st = (line.split("\t") + ["", ""])[:3]
        if en and zh:
            canon[en], status[en] = zh, st
    variants = {en: [v for v in r2["variants"].get(en, []) if v and v != zh] for en, zh in canon.items()}
    pats = {en: re.compile(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])", re.I) for en in canon}

    def fix(english, chinese):
        names = [en for en in canon if en.lower() in english.lower() and pats[en].search(english)]
        if not names:
            return chinese
        shield = {}
        out = chinese
        for i, zh in enumerate(sorted({canon[en] for en in names}, key=len, reverse=True)):
            tok = f"{i}"
            shield[tok] = zh
            out = out.replace(zh, tok)
        for v in sorted({v for en in names for v in variants[en]}, key=len, reverse=True):
            en = next(e for e in names if v in variants[e])
            out = out.replace(v, canon[en])
        for tok, zh in shield.items():
            out = out.replace(tok, zh)
        return out

    changed = 0
    for f in sorted((ROOT / "translations" / "zhCN" / "stories").glob("*.json")):
        src = ROOT / "work" / "tr-story-in" / f"{f.stem}.en.json"
        if not src.exists():
            continue
        en_all, zh_all = load(src), load(f)
        for k, v in zh_all.items():
            en_secs = {s["i"]: s for s in en_all.get(k, {}).get("sec", [])}
            for s in v["sec"]:
                e = en_secs.get(s["i"], {})
                for x in ("t", "b"):
                    if x in s:
                        new = fix(e.get(x, "") + " " + e.get("t", ""), s[x])
                        changed += new != s[x]
                        s[x] = new
        f.write_text(json.dumps(zh_all, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in sorted((ROOT / "translations" / "zhCN" / "extras").glob("*.json")):
        src = ROOT / "work" / "tr-extra-in" / f"{f.stem}.en.json"
        if not src.exists():
            continue
        en_all, zh_all = load(src), load(f)
        for k, v in zh_all.items():
            e = en_all.get(k, {})
            new = fix(e.get("en", "") + " " + str(e.get("context") or ""), v["zh"])
            changed += new != v["zh"]
            v["zh"] = new
        f.write_text(json.dumps(zh_all, ensure_ascii=False, indent=1), encoding="utf-8")
    gl = ROOT / "glossary" / "zhCN.tsv"
    have = {tuple(l.split("\t")[:2]) for l in gl.read_text(encoding="utf-8").splitlines()}
    with open(gl, "a", encoding="utf-8") as out:
        for en, zh in sorted(canon.items()):
            if (en, zh) not in have:
                out.write(f"{en}\t{zh}\tname\t{status.get(en) or 'canonical'}\n")
    print(f"{len(canon)} names, {changed} texts changed")


if __name__ == "__main__":
    main(*sys.argv[1:3])
