"""Unit tests for the hash rules and pack-format helpers (stdlib only; the add-on files aren't in git)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import lfcommon as lf  # noqa: E402

# npc:agathelos-the-raging from Lore Forever 1.4.0 (Data/Z_razorfenkraul.lua): core clipHash "f34341", fullclips "144ea9".
AGATHELOS = {
    "n": "Agathelos the Raging",
    "s": "Deep within Razorfen Kraul, Agathelos the Raging is held among the thorned tunnels. The quilboar revere "
         "Agamaggan as their god and progenitor, and Agathelos’s great size carries spiritual meaning. His armor and "
         "fury make him one of the most dangerous beasts beneath the southern Barrens.",
    "sec": [
        {"t": "Avatars of the Great Boar", "sp": 0,
         "b": "Agamaggan, the titanic boar, is god and progenitor to the quilboar. So among the Razorfen tribes, a beast "
              "as large as Agathelos carries deep spiritual meaning. He stands roughly twice as tall as a Barrens "
              "thunder lizard."},
        {"t": "Kept in Chains", "sp": 0,
         "b": "The quilboar keep Agathelos from roaming freely through the Kraul. Several guards maintain a field before "
              "the short, dead-end tunnel where he is penned. Intruders who break through that barrier face a raging "
              "beast, made more fearsome still by his fury."},
    ],
}


class HashRules(unittest.TestCase):
    def test_overview_hash_matches_core(self):
        self.assertEqual(lf.sha6(lf.overview_text(AGATHELOS)), "f34341")

    def test_full_story_hash_matches_fullclips(self):
        full = " ".join([AGATHELOS["n"] + ". " + AGATHELOS["s"]] + [s["b"] for s in AGATHELOS["sec"]])
        self.assertEqual(lf.sha6(full), "144ea9")

    def test_spoiler_section_is_left_out(self):
        e = json.loads(json.dumps(AGATHELOS))
        e["sec"][0]["sp"] = 1
        self.assertEqual(lf.overview_text(e), lf.ws(e["n"] + ". " + e["s"]))

    def test_spoiler_flags_come_from_english(self):
        zh = {"n": "名", "s": "概要。", "sec": [{"t": "标题", "b": "正文。"}]}
        en = {"n": "Name", "s": "Summary.", "sec": [{"t": "Title", "b": "Body.", "sp": 2}]}
        self.assertEqual(lf.overview_text(zh, en), "名. 概要。")
        self.assertEqual(lf.spoken_zh(zh, en), "名。概要。")

    def test_fingerprint_is_utf8_bytes(self):
        e = {"n": "Agathelos’s", "s": "ab", "sec": [{"t": "t", "b": "bb", "sp": 1}],
             "faq": [{"q": "q?", "a": "a", "add": "x"}, {"q": "qq", "a": "aaa"}]}
        self.assertEqual(lf.fingerprint(e), "13,2,1.2.1,2.3.0")

    def test_clip_stem_matches_voice_clippath(self):
        self.assertEqual(lf.clip_stem("zone:stormwind"), "zone_stormwind")
        self.assertEqual(lf.clip_stem("quest:176#detail"), "quest_176__detail")
        self.assertEqual(lf.clip_stem("item:bartleby-s-mug"), "item_bartleby-s-mug")

    def test_pack_names_have_no_locale_suffix(self):
        # A name ending in _xxXX would make the pack that language's voice (Voice.KeyOf), silent over English text.
        import re
        for pk in lf.PACKS:
            self.assertIsNone(re.search(r"_[a-z]{2}[A-Z]{2}$", lf.zh_pack(pk)), pk)
        self.assertEqual(lf.zh_pack("Female"), "LoreForever_Voice_ChineseFemale")
        self.assertEqual(lf.zh_pack("MorePeople"), "LoreForever_Voice_ChineseFemale_MorePeople")

    def test_lua_string_escapes(self):
        self.assertEqual(lf.lua_str('a"b\\c\nd'), '"a\\"b\\\\c\\nd"')
        self.assertEqual(lf.lua_val({"hash": "abc", "sectionIndex": 1}), '{hash="abc",sectionIndex=1}')


class Manifest(unittest.TestCase):
    def test_manifest_rows_are_consistent(self):
        rows = lf.read_jsonl(ROOT / "manifest" / "clips.jsonl")
        self.assertTrue(rows)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for r in rows:
            self.assertTrue(r["pack"].startswith(lf.VOICE), r["id"])
            self.assertEqual(r["stem"], lf.clip_stem(r["id"]))
            if r.get("status") == "recorded":
                self.assertGreater(r["duration"], 0, r["id"])
                self.assertTrue(r["zh_text"], r["id"])


if __name__ == "__main__":
    unittest.main()
