"""Load Lore Forever add-on files in a real Lua 5.1 (lupa) and convert tables to Python.

Packs are loaded through a fake LoreForeverPacks.Begin that returns one table per pack name (as the add-on does),
so the files run exactly as the game runs them.
"""
import re
from pathlib import Path

from lupa import lua51

FAKE_BEGIN = """
_PACKS = {}
LoreForeverPacks = { Begin = function(name)
  if _PACKS[name] then return _PACKS[name] end
  local P = setmetatable({}, {__index = function(t, k) local v = {}; rawset(t, k, v); return v end})
  _PACKS[name] = P
  return P
end }
"""


def runtime():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(FAKE_BEGIN)
    return L


def to_py(v):
    if lua51.lua_type(v) == "table":
        keys = list(v.keys())
        if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
            return [to_py(v[k]) for k in sorted(keys)]
        return {str(k): to_py(v[k]) for k in keys}
    return v


def script_files(folder):
    """The Lua files a .toc loads, in order (following .xml includes)."""
    folder = Path(folder)
    toc = next(folder.glob("*.toc"))
    out = []
    for line in toc.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(".xml"):
            out += re.findall(r'<Script file="([^"]+)"', (folder / line).read_text(encoding="utf-8"))
        else:
            out.append(line)
    return out


def run_file(L, path, *args):
    loader = L.execute("return function(src, name) local f, err = loadstring(src, name); return f, err end")
    fn, err = loader(Path(path).read_text(encoding="utf-8"), "@" + Path(path).name)
    if fn is None:
        raise RuntimeError(f"{path}: {err}")
    fn(*args)


def load_pack(L, folder, skip=("Search_",)):
    folder = Path(folder)
    for f in script_files(folder):
        if any(f.startswith(s) for s in skip):
            continue
        run_file(L, folder / f, folder.name, L.table())
    P = L.globals()._PACKS[folder.name]
    return {k: to_py(P[k]) for k in P.keys()} if P is not None else {}


def toc_fields(folder):
    folder = Path(folder)
    toc = next(folder.glob("*.toc"))
    out = {}
    for line in toc.read_text(encoding="utf-8").splitlines():
        m = re.match(r"##\s*([^:]+):\s*(.*)$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def load_core(addons):
    L = runtime()
    ns = L.table()
    data = Path(addons) / "LoreForever" / "Data"
    for f in re.findall(r'<Script file="([^"]+)"', (data / "Data.xml").read_text(encoding="utf-8")):
        if f.startswith(("Search_", "Vectors_")):
            continue
        run_file(L, data / f, "LoreForever", ns)
    db = ns.DB
    return {k: to_py(db[k]) for k in ["version", "entries", "clipHash", "fullclips", "clipPack", "clipNarrator",
                                       "answerHash", "questVoice", "questClip", "recaps"] if db[k] is not None}
