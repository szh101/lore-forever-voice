# REPORT — Chinese female narration for Lore Forever (pilot-1)

Built on 2026-11-08 on the owner's Apple Silicon Mac. Status: **pilot only**, waiting for an in-game test.

## Change from INSTRUCTIONS.md: voice only, text stays English

The owner decided (2026-11-08) to keep Lore Forever's text in **English** and only hear it narrated in **Chinese**.
So there is **no `LoreForever_Lang_zhCN`** and no `_zhCN` voice packs: a pack named `..._zhCN` or with
`X-LoreForever-Locale: zhCN` only plays while the add-on shows Chinese (Voice.Unusable / Voice.KeyOf).

Instead the packs are a **separate narrator**, `LoreForever_Voice_ChineseFemale`, with `X-LoreForever-Locale: enUS`,
and lands/story packs that extend it, mirroring the English female split:

| English pack | Chinese narration pack |
|---|---|
| LoreForever_Voice_Female | LoreForever_Voice_ChineseFemale (`X-LoreForever-Sample: zone:stormwind`) |
| LoreForever_Voice_Female_Alliance / _Horde | LoreForever_Voice_ChineseFemale_Alliance / _Horde |
| _MoreItems / _MorePeople / _MorePlaces | LoreForever_Voice_ChineseFemale_MoreItems / ... |
| _Quests / _Quests2 / _Quests3 | (quest dialogue: not in the pilot) |
| _MoreQuests1 / 2 / 3 | LoreForever_Voice_ChineseFemale_MoreQuests1 / ... |

Each recording is a **community-voice scoped clip** (`P.scopedVersion = 1`, `P.scopedClips[id]` with
`scope = "overview-body"`, the Chinese name, summary and section it reads; see Voice.ScopedClip). That means:

- it plays while the add-on shows English (the pack is enUS);
- the subtitles / read-along show the **Chinese words actually spoken** (Voice.Play sets `lastClip.text` from the
  scoped row), not English words that don't match;
- it keeps playing when the add-on rewords the English later (a scoped clip plays with its own words, "whatever our
  English or translation says now"), so add-on updates don't silence it. `c[id]` and `sourceHash` hold the English
  `clipHash` it was recorded from, so `manifest/clips.jsonl` can tell which recordings are behind the English.

## Version: Lore Forever 1.4.0, not 1.3.0

INSTRUCTIONS.md names 1.3.0. CurseForge published **1.4.0 on 2026-11-08**, and the CurseForge app updates the add-on
on the gaming PC automatically, so the work uses **1.4.0** (core data version `2026-11-08 16:43 UTC`):

| Pack | Version | Clips (`c["..."]`) | INSTRUCTIONS.md (1.3.0) |
|---|---|---:|---:|
| LoreForever_Voice_Female | 1.4.0 | 198 | 198 |
| _Alliance | 1.4.0 | 385 | 385 |
| _Horde | 1.4.0 | 296 | 296 |
| _MoreItems | 1.4.0 | 2,433 | 2,435 |
| _MorePeople | 1.4.0 | 2,500 | 2,500 |
| _MorePlaces | 1.4.0 | 2,392 | 2,392 |
| _Quests | 1.4.0 | 4,135 | 4,104 |
| _Quests2 | 1.4.0 | 3,683 | 3,535 |
| _Quests3 | **1.1.0** (newest on CurseForge) | 4,709 | 4,709 |
| _MoreQuests1 | 1.4.0 | 3,688 | 3,688 |
| _MoreQuests2 | 1.4.0 | 5,261 | 5,261 |
| _MoreQuests3 | 1.4.0 | 2,083 | 1,953 |
| **Total** | | **31,763** | 31,456 |

INSTRUCTIONS.md gives the total as 35,456, but its per-pack numbers add up to 31,456 (an addition slip).
MoreItems ships inside the "item stories and quest stories 40+" download.

## How the hashes work (and how they were verified)

The add-on has no narration hash code in Lua (its djb2 / CRC helpers match none of the values); the author's Python
build makes them. The rule was derived from the data and checked against the shipped packs (`scripts/extract.py`,
`work/hash-verification.json`):

- `clipHash[key] = sha1(T).hexdigest()[:6]`, `T` = whitespace-collapsed `name + ". " + summary`, plus
  `" " + section[1].body` when section 1 exists and the **English** entry doesn't flag it as a spoiler (`sp == 0`).
- English: **5,053 / 5,063** entry clips reproduce `ns.DB.clipHash` (99.80%).
- French, recomputed from the French text of `LoreForever_Lang_frFR`: **5,053 / 5,063** reproduce its
  `P.clipHash` (99.80%). The 10 misses are the same keys in both (e.g. `quest:7782`, `item:bloodstone-choker`):
  stale rows in the add-on's own data, not a different rule.
- Complete stories: `fullclips` / Transport `fullHash = sha1(full story text)[:6]` (checked on
  `npc:agathelos-the-raging`). Not used here: like the French packs, the Chinese packs record each entry's overview.
- `Lang.Fingerprint` (`scripts/lfcommon.py: fingerprint`) matches the frFR pack's `fp` for 4,983 entries; the other
  146 are French translations of older English. It is used only to notice when the English of an entry changed.

So each Chinese recording reads exactly the parts the English overview reads (name, summary, and section 1 unless it's
a spoiler), translated.

## What pilot-1 contains

32 entries around Stormwind and Elwynn Forest:

- `LoreForever_Voice_ChineseFemale`: Stormwind City (the sample), Elwynn Forest, Northshire Abbey
- `_Alliance`: Bolvar Fordragon, Marshal Dughan, Goldshire, Cathedral of Light, Old Town, Stormwind Keep,
  Lion's Pride Inn
- `_MorePeople`: Hogger, Archbishop Benedictus, Innkeeper Farley, Ma Stonefield, Gramma Stonefield, Bartleby,
  Morgan the Collector, Supervisor Raelen
- `_MoreItems`: Report on the Defias Brotherhood, Defias Docket, Bartleby's Mug, Gold Dust, Huge Gnoll Claw,
  Marshal Haggard's Badge, Bundle of Wood
- `_MoreQuests1`: Wanted: "Hogger", Brotherhood of Thieves, Bounty on Murlocs, Riverpaw Gnoll Bounty,
  Gold Dust Exchange, Bartleby the Drunk, Messenger to Stormwind

Each pack: toc, `Clips.lua` (`c[id]`, `P.scopedClips`, `P.len[id]` in tenths of a second from the MP3),
`Audio/<stem>.mp3`, `CREDITS.txt`.

Audio: the owner's AI documentary voice (Qwen3-TTS 1.7B Base on MLX, the revision pinned in its voice.json,
temperature 0.9, `lang_code="Chinese"`, reference audio + its exact transcript on every call), text split at sentence
ends (≤ 600 characters per call, 0.25 s silence between pieces), leading/trailing silence trimmed, normalised to
−19 LUFS / −1.5 dBTP (the English female MP3s measure about −19 LUFS), 44.1 kHz mono MP3 at 64 kb/s like the English
packs. The reference recording itself is not in this repo or in any release.

### Pilot numbers

| Pack | Clips | Audio |
|---|---:|---:|
| LoreForever_Voice_ChineseFemale | 3 | 2.3 min |
| LoreForever_Voice_ChineseFemale_Alliance | 7 | 5.0 min |
| LoreForever_Voice_ChineseFemale_MoreItems | 7 | 3.7 min |
| LoreForever_Voice_ChineseFemale_MorePeople | 8 | 4.9 min |
| LoreForever_Voice_ChineseFemale_MoreQuests1 | 7 | 4.0 min |

32 clips, 19.9 minutes of audio, 6,669 Chinese characters, recorded in
26 minutes on this Mac. Speaking rate 5.13–6.05 characters per
second for every clip (no clip cut short or running on). `scripts/selfcheck.py` passed: every pack loads in Lua 5.1, its toc
fields are right, every `c[id]` is the add-on's current English `clipHash`, and the add-on's own `Voice.ScopedClip` and
`Voice.ClipCurrent` (run from its Voice.lua) accept every clip with English shown and return its Chinese words; every MP3
and `P.len` is there (`build/selfcheck.json` in the release manifest).

## Not done / uncertain — check these in the game

1. **Turn the narrator on.** A new voice goes to the bottom of the narrator list (Voice adoptNew). In
   Options > Narration voices, move "Lore Forever Chinese female narrator" to the top. Stories it hasn't recorded
   then fall back to the next voice (or show as text, depending on the fill-in setting).
2. **Chinese subtitles on an English client.** The add-on draws with the game's own fonts; its code assumes an enUS
   client draws Chinese as boxes (Packs.Drawable). If the subtitles show boxes, turn subtitles off (the ⋯ menu:
   "Show subtitles"); the narration itself is unaffected.
3. Quest giver dialogue (`_Quests*`: `#detail` / `#progress` / `#complete`) is not in the pilot. It needs the quest
   packs' format (`P.questVoice` fingerprints, `P.questText` for subtitles, Voice.QuestClip).
4. Spoken section headings and complete stories (`#title`, `#headN`, `#sectionN`, Transport) aren't recorded: each
   entry is narrated as its overview, as the French packs do.
5. Proper nouns use mainland-China (国服) names from memory, not checked against a zhCN client.
   `glossary/zhCN.tsv` marks the less certain ones (`status = uncertain`).
6. The clips were checked for loudness, duration and speaking rate, not listened to one by one.

## Full run (after the pilot is approved)

The 9 lore packs hold **5,165 overview clips** (Female 198, Alliance 385, Horde 296, MoreItems 741, MorePeople 583,
MorePlaces 413, MoreQuests1 851, MoreQuests2 1,314, MoreQuests3 384); the rest of their 31,763 clip ids are section
headings, story pieces and book pages of the English complete stories, which these packs don't record. Only the spoken
parts need translating (name, summary, section 1). At the pilot's pace (37 s of audio per clip on average, about
1.3 minutes of computing per minute of audio) that is roughly **53 hours of audio, about 70 hours of recording** on this
Mac, resumable across days through `manifest/clips.jsonl`. Quest giver dialogue (the 3 `_Quests` packs, 12,527 pages)
would be a separate step after that.

## Re-running

```
python scripts/extract.py --addons addons --work work           # CurseForge folders -> work/*.json, hash check
python scripts/build.py prepare --scope pilot                    # translations -> manifest/clips.jsonl
<mlx venv>/python scripts/tts_zh.py --voice <documentary-voice> --model <qwen3-tts dir>   # records pending rows
python scripts/build.py packs --out build                        # add-on folders
python scripts/selfcheck.py --build build --addons addons --json build/selfcheck.json
python scripts/release.py --build build --dist dist --tag pilot-1
```

`lupa` (for the Lua 5.1 checks) and `imageio-ffmpeg` (MP3 encoding) are the only extra Python packages.
