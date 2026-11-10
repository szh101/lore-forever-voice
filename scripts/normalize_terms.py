"""Make proper nouns consistent across the full run's translation batches.

  python scripts/normalize_terms.py work/terms-canon-*.tsv

The batches were translated in parallel, so one English name sometimes got different Chinese renderings. For each
entry whose English contains a name, every other rendering of it seen in the batches (_new_terms) is replaced by the
chosen one (en<TAB>zh<TAB>status). Edits work/tr-out/full-NN.zh.json in place and adds the names to the glossary.
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN, OUT = ROOT / "work" / "tr-in", ROOT / "work" / "tr-out"


def main(paths):
    canon = {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines()[1:]:
            en, zh, status = (line.split("\t") + ["", ""])[:3]
            if en and zh:
                canon[en] = (zh, status)
    variants = collections.defaultdict(set)
    for f in OUT.glob("full-*.zh.json"):
        for t in json.loads(f.read_text()).get("_new_terms", []):
            if len(t) >= 2 and t[0] in canon:
                variants[t[0]].add(t[1])
    pats = {en: re.compile(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])") for en in canon}
    changed = 0
    for src in sorted(IN.glob("full-*.en.json")):
        n = src.name.split(".")[0]
        en_all, zp = json.loads(src.read_text()), OUT / f"{n}.zh.json"
        zh_all = json.loads(zp.read_text())
        for k, e in en_all.items():
            text = " ".join([e["n"], e["s"], e.get("sec_b", "")])
            names = [zh for en, (zh, _) in canon.items() if en in text and pats[en].search(text)]
            subs = []
            for en, (zh, _) in canon.items():
                if en in text and pats[en].search(text):
                    subs += [(v, zh) for v in variants[en] if v != zh and len(v) > 1]
            subs.sort(key=lambda s: -len(s[0]))
            # Repair an earlier pass that replaced inside another chosen name (尼尔鲁·火刃 -> 尼尔鲁·燃烧之刃).
            repair = []
            for zh in names:
                bad = zh
                for v, c in subs:
                    if v not in c:
                        bad = bad.replace(v, c)
                if bad != zh:
                    repair.append((bad, zh))
            z = zh_all[k]
            for field in ("n", "s", "sec_b"):
                if field in z:
                    new = z[field]
                    for bad, zh in repair:
                        new = new.replace(bad, zh)
                    # Shield every chosen name in this entry, then replace the other renderings.
                    shield = sorted(set(names), key=len, reverse=True)
                    for i, zh in enumerate(shield):
                        new = new.replace(zh, f"\uE000{i}\uE001")
                    for v, zh in subs:
                        new = new.replace(v, f"\uE000{shield.index(zh)}\uE001")
                    for i, zh in enumerate(shield):
                        new = new.replace(f"\uE000{i}\uE001", zh)
                    if new != z[field]:
                        z[field], changed = new, changed + 1
        zp.write_text(json.dumps(zh_all, ensure_ascii=False, indent=1))
    g = ROOT / "glossary" / "zhCN.tsv"
    have = {l.split("\t")[0] for l in g.read_text(encoding="utf-8").splitlines()[1:]}
    with open(g, "a", encoding="utf-8") as f:
        for en, (zh, status) in sorted(canon.items()):
            if en not in have:
                f.write(f"{en}\t{zh}\tterm\t{status or 'uncertain'}\n")
    print(f"{len(canon)} names, {changed} fields changed")


if __name__ == "__main__":
    main(sys.argv[1:])
