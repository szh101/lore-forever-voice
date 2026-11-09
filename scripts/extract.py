"""Read the CurseForge add-on folders (addons/) into work/ JSON and verify the hash rule.

  python scripts/extract.py --addons addons --work work

Writes work/core.json, work/packs.json and work/hash-verification.json. Exits non-zero if the hash rule doesn't
reproduce the shipped frFR and enUS clipHash values (allowing the handful of stale English rows noted in REPORT.md).
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import PACKS, dump_json, en_pack, overview_text, sha6, fingerprint  # noqa: E402
import luaload  # noqa: E402


def verify(entries, clip_hash, label, english):
    c = collections.Counter()
    misses = []
    for k, h in clip_hash.items():
        if "#" in k or k not in entries:
            continue
        ok = sha6(overview_text(entries[k], english.get(k))) == h
        c[ok] += 1
        if not ok:
            misses.append(k)
    total = c[True] + c[False]
    return {"label": label, "checked": total, "match": c[True], "rate": round(c[True] / total, 5) if total else None,
            "misses": sorted(misses)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addons", default="addons")
    ap.add_argument("--work", default="work")
    a = ap.parse_args()
    addons, work = Path(a.addons), Path(a.work)

    core = luaload.load_core(addons)
    dump_json(work / "core.json", core)
    print("core", core["version"], "entries", len(core["entries"]), "clipHash", len(core["clipHash"]))

    L = luaload.runtime()
    packs, tocs = {}, {}
    names = ["LoreForever_Lang_frFR", "LoreForever_Voice_Female_MorePeople_frFR"] + [en_pack(p) for p in PACKS]
    for n in names:
        if (addons / n).is_dir():
            packs[n] = luaload.load_pack(L, addons / n)
            tocs[n] = luaload.toc_fields(addons / n)
            print(n, tocs[n].get("Version"), "clips", len(packs[n].get("clips", {})))
    dump_json(work / "packs.json", packs)
    dump_json(work / "tocs.json", tocs)

    # The frFR language pack stores its fingerprint of the English for each entry; check ours equals it.
    fr = packs["LoreForever_Lang_frFR"]
    fp = collections.Counter(fingerprint(core["entries"][k]) == t.get("fp")
                             for k, t in fr["entries"].items() if k in core["entries"] and t.get("fp"))
    report = {
        "enUS": verify(core["entries"], core["clipHash"], "core clipHash from English entries", core["entries"]),
        "frFR": verify(fr["entries"], fr["clipHash"], "frFR clipHash from French entries", core["entries"]),
        "fingerprint_vs_frFR_fp": {"match": fp[True], "differ": fp[False]},
    }
    dump_json(work / "hash-verification.json", report)
    for k in ("enUS", "frFR"):
        r = report[k]
        print(f"{k}: {r['match']}/{r['checked']} ({r['rate']:.2%}) misses {len(r['misses'])}")
    print("fingerprint vs frFR fp:", report["fingerprint_vs_frFR_fp"])
    if report["enUS"]["rate"] < 0.995 or report["frFR"]["rate"] < 0.99:
        sys.exit("hash rule does not reproduce the shipped values; stop and investigate")


if __name__ == "__main__":
    main()
