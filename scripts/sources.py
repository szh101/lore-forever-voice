"""The English the game shows for quest pages and book pages, from the cmangos classic-db dump (extras.py reads it).

  python3 scripts/sources.py [--sql work/sources/classic.sql.gz]

Writes work/sources/quests.json ({quest id: {title, detail, progress, complete}}, every quest in the dump) and
work/sources/books.json ({booktext:<title>#<page>: text}, for each book page work/core.json's clipHash names). A book
is an item (item_template.PageText) or a game object of type 9 (data0) whose lowercased name is the title; its pages
follow page_text.next_page. A page's text is kept when its sha1 (as extras.py checks) gives the add-on's hash, else
the page in that position of the first chain long enough (extras.py then marks it unverified).
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import ROOT, load_json  # noqa: E402

SRC = ROOT / "work" / "sources"


def table(sql, name):
    m = re.search(r"CREATE TABLE `%s` \((.*?)\n\)" % name, sql, re.S)
    cols = re.findall(r"^\s*`(\w+)`", m.group(1), re.M)
    out = []
    for m in re.finditer(r"INSERT INTO `%s` (?:\([^)]*\) )?VALUES\s*(.*?);\n" % name, sql, re.S):
        s, i, n = m.group(1), 0, len(m.group(1))
        while i < n:
            if s[i] != "(":
                i += 1
                continue
            vals, cur, inq = [], "", False
            i += 1
            while True:
                c = s[i]
                if inq:
                    if c == "\\":
                        cur += {"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(s[i + 1], s[i + 1])
                        i += 2
                        continue
                    if c == "'":
                        if i + 1 < n and s[i + 1] == "'":
                            cur += "'"
                            i += 2
                            continue
                        inq = False
                    else:
                        cur += c
                    i += 1
                    continue
                if c == "'":
                    inq = True
                elif c == ",":
                    vals.append(cur)
                    cur = ""
                elif c == ")":
                    vals.append(cur)
                    i += 1
                    break
                else:
                    cur += c
                i += 1
            out.append(dict(zip(cols, vals)))
    return out


def ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", default=str(SRC / "classic.sql.gz"))
    a = ap.parse_args()
    with gzip.open(a.sql, "rt", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    quests = {r["entry"]: {"title": r["Title"], "detail": r["Details"], "progress": r["RequestItemsText"],
                           "complete": r["OfferRewardText"]} for r in table(sql, "quest_template")}
    (SRC / "quests.json").write_text(json.dumps(quests), encoding="utf-8")
    print("quests", len(quests))

    pages = {r["entry"]: r for r in table(sql, "page_text")}
    titles = {}
    for r in table(sql, "item_template"):
        if r.get("PageText", "0") != "0":
            titles.setdefault(r["name"].lower(), set()).add(r["PageText"])
    for r in table(sql, "gameobject_template"):
        if r.get("type") == "9" and r.get("data0", "0") != "0":
            titles.setdefault(r["name"].lower(), set()).add(r["data0"])

    def chain(p):
        out, seen = [], set()
        while p and p != "0" and p in pages and p not in seen:
            seen.add(p)
            out.append(pages[p]["text"])
            p = pages[p]["next_page"]
        return out

    ch = load_json(ROOT / "work" / "core.json")["clipHash"]
    st, books = collections.Counter(), {}
    for k in (k for k in ch if k.startswith("booktext:")):
        t, n = k[9:].rsplit("#", 1)
        ok = anyp = None
        for p in titles.get(t, ()):
            c = chain(p)
            if len(c) >= int(n):
                anyp = c[int(n) - 1]
                for v in (anyp, re.sub(r"\$[bB]", "\n", anyp), re.sub(r"\$[bB]", " ", anyp)):
                    if hashlib.sha1(ws(v).encode()).hexdigest()[:6] == ch[k]:
                        ok = anyp
        st["match" if ok else "text, no hash match" if anyp else "no source"] += 1
        if ok or anyp:
            books[k] = ok or anyp
    (SRC / "books.json").write_text(json.dumps(books), encoding="utf-8")
    print("book pages", dict(st))


if __name__ == "__main__":
    main()
