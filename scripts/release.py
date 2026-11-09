"""Zip each built add-on folder and write release-manifest.json (for a GitHub Release).

  python scripts/release.py --build build --dist dist --tag pilot-1
  gh release create pilot-1 dist/pilot-1/* --title ... --notes-file ...

A folder over --max-bytes is split by its Audio/ subfolders into <folder>.part1.zip, .part2.zip ... (unzip all parts
into the same AddOns folder).
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lfcommon import CORE_VERSION, LOCALE, load_json  # noqa: E402


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def zip_files(dst, folder, files):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):
            z.write(f, Path(folder.name) / f.relative_to(folder))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--max-bytes", type=int, default=1_900_000_000)
    a = ap.parse_args()
    build, out = Path(a.build), Path(a.dist) / a.tag
    out.mkdir(parents=True, exist_ok=True)
    selfcheck = build / "selfcheck.json"
    if not selfcheck.exists() or not load_json(selfcheck).get("ok"):
        sys.exit("run scripts/selfcheck.py --json build/selfcheck.json first; it must pass")
    assets = []
    for folder in sorted(p for p in build.iterdir() if p.is_dir()):
        files = [f for f in folder.rglob("*") if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        groups = [files]
        if size > a.max_bytes:
            groups, cur, cur_size = [], [], 0
            for f in sorted(files):
                if cur and cur_size + f.stat().st_size > a.max_bytes:
                    groups.append(cur)
                    cur, cur_size = [], 0
                cur.append(f)
                cur_size += f.stat().st_size
            groups.append(cur)
        for i, g in enumerate(groups, 1):
            name = f"{folder.name}.zip" if len(groups) == 1 else f"{folder.name}.part{i}.zip"
            zip_files(out / name, folder, g)
            assets.append({"file": name, "folder": folder.name, "part": i, "parts": len(groups),
                           "files": len(g), "size": (out / name).stat().st_size, "sha256": sha256(out / name)})
            print(name, assets[-1]["size"])
    manifest = {"tag": a.tag, "locale": LOCALE, "lore_forever_core_version": CORE_VERSION,
                "core_data_version": load_json(Path("work/core.json"))["version"] if Path("work/core.json").exists() else None,
                "install_to": r"World of Warcraft\_forever_\Interface\AddOns", "assets": assets,
                "selfcheck": load_json(selfcheck)["packs"]}
    (out / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", out / "release-manifest.json")


if __name__ == "__main__":
    main()
