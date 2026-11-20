# Updating after a Lore Forever release / Lore Forever 更新后补语音

When mikeliudev publishes a new Lore Forever version, only the stories that are new or whose English changed need
new Chinese. Everything else keeps its recording. The released packs never stop working: each recording plays with
its own Chinese subtitle, whatever the English says now, so an update only leaves new stories unvoiced (they fall
back to the player's next narrator) until the next pack release.

插件作者发布新版后，只需要给**新增**和**英文改过**的条目做中文；其余录音原样保留。旧的语音包在新版插件里照样能播，
只是新增的故事暂时没有中文，会由玩家的下一个旁白来读。

This runs on the Mac that has the voice and the model (REPORT.md, "Re-running"). `<mlx>` below is
`~/Workspace/voice-studio/.venv/bin/python`; `<lua>` is a Python with `lupa` for the self-check
(`work/venv-lua/bin/python`; to make one: `python3 -m venv work/venv-lua && work/venv-lua/bin/pip install lupa`).

## 1. Stop the recorder, if one is running

```
python3 scripts/update.py status        # also says if a batch is still out for translation
pkill -f scripts/fullrun.py; pkill -f scripts/storyrun.py; pkill -f scripts/tts_zh.py
```

The manifest is saved after every clip, so stopping at any point loses at most the clip being recorded.

## 2. Get the new add-on

Download the new **Lore Forever** core (CurseForge project 1715510) and the **English female** packs, and replace
the folders in `addons/` (git-ignored: never commit them; keep the old copy, e.g. in `work/backup-<version>/`, until
the new release is out). Each female pack is a CurseForge project of its own (newest file of each:
`https://www.curseforge.com/api/v1/mods/<project>/files?pageSize=1&sort=dateCreated&sortDescending=true`, then
`.../files/<file id>/download`):

| pack | project | pack | project |
|---|---|---|---|
| Female | 1727332 | Quests | 1727333 |
| Female_Alliance | 1767708 | Quests2 | 1766731 |
| Female_Horde | 1740579 | Quests3 | 1766732 |
| Female_MoreItems | 1809088 | MoreQuests1 | 1767789 |
| Female_MorePeople | 1743604 | MoreQuests2 | 1767791 |
| Female_MorePlaces | 1743315 | MoreQuests3 | 1767942 |
| Female_MorePeople_frFR (+ Lang_frFR, for the hash check) | 1767784 | | |

Not every pack is re-released with each core; that's fine. If one is missing from this list, search CurseForge for
"Lore Forever female narrator". Then:

```
<lua> scripts/extract.py --addons addons --work work
python3 scripts/sources.py      # quest and book page English from the cmangos dump, for the new clip list
```

It must pass the hash check. Then set `CORE_VERSION` in `scripts/lfcommon.py` to the new version (it goes into
each pack's .toc and the release manifest). If the author added or renamed an English female pack, add it to
`PACKS` there too.

Check the things REPORT.md checked for 1.4.0 against the new core: `Voice.Play`'s scoped-clip path
(`P.scopedVersion`, `P.scopedClips`), and that an enUS narrator with `Extends` still loads. If those changed, the pack
format in `scripts/build.py packs` must follow before anything is recorded.

## 3. Find what needs translating

```
python3 scripts/update.py export
```

This rebuilds `manifest/clips.jsonl` against the new English and writes the entries that need Chinese to
`work/tr-in/upd-YYYYMMDD-NN.en.json` (150 per batch):

- **untranslated**: a story that is new in this version;
- **retranslate**: a story whose spoken English (name, summary, first section) changed. Its old recording is
  dropped from the packs until the new one is recorded. Its old Chinese is in the batch as `prev`, to keep wording
  where the English didn't change.

A story the author removed simply leaves the manifest. `python3 scripts/update.py status` shows the counts.

The complete stories and the quest/recap/book pages have their own exports:

```
<mlx> scripts/stories.py export --batches 2      # work/tr-story-in/story-NN.en.json
<mlx> scripts/extras.py export --chars 40000     # work/tr-extra-in/{quest,book,recap}-NN.en.json
```

What doesn't need new Chinese is kept: a clip the author moved to another pack keeps its recording (same id, same
Chinese); a quest page whose hash changed but whose English is the one we translated keeps its Chinese (extras.py
re-stamps it). A changed story's batch lists every section; give each section the old Chinese as `prev_t`/`prev_b`
where its English is unchanged, and have the translator copy those exactly, so the recordings are reused (the
1.15.0 update did this: 123 of 127 parts copied).

## 4. Translate

One translator per batch file (a Claude subagent per batch works well; give each its own batch and nothing else, so
they can't overwrite each other). The brief used for the first 32 batches:

> Translate World of Warcraft lore text (from the Lore Forever add-on, adapted from Warcraft Wiki, CC BY-SA 4.0) into
> natural, spoken-style Simplified Chinese. A calm documentary narrator reads it aloud with a TTS voice.
>
> Input: `work/tr-in/<batch>.en.json`, keyed by entry id. Each value has `n` (name), `s` (summary) and sometimes
> `sec_b` (a paragraph read after the summary). Ignore `src`. `prev`, when present, is the Chinese for the older
> English: keep its wording wherever the English didn't change.
>
> Glossary: `glossary/zhCN.tsv` (en, zh, type, status). Use those Chinese names exactly. For other proper nouns use
> the official mainland China (国服) WoW translation when you know it confidently; otherwise choose the best rendering
> and list it in `_new_terms` as "uncertain".
>
> Write `work/tr-out/<batch>.zh.json`: the same ids, each `{"n", "s", and "sec_b" only if the input has it}`, plus a
> top-level `"_new_terms": [[english, chinese, "official"|"uncertain"], ...]`.
>
> - Fluent Chinese for listening, not word-for-word; full-width punctuation; no English left in the text. Spell
>   out what a narrator would say: symbols (% → 百分之), and Latin codes in names (OOX-17/TN → OOX十七TN).
> - Don't add or drop facts. Keep ids unchanged. `n` is just the name (no trailing 。).
> - Work in groups of 25–40 entries, merging into the output file as you go.
> - At the end validate: the file parses, has exactly the input's ids, every value has `n` and `s`, and `sec_b`
>   exactly when the input does, and nothing is empty.

Afterwards look over `glossary/new-terms-full.tsv` (new names land there when a batch is taken) and add the ones you
settle on to `glossary/zhCN.tsv`. If two batches rendered one name differently, fix the batch files in `work/tr-out/`
before the recorder takes them (`scripts/normalize_terms.py` did this for the first run).

## 5. Record and release

Pick a new release tag, `zhCN-<Lore Forever version>-1` (for example `zhCN-1.5.0-1`), then:

```
nohup caffeinate -is <mlx> scripts/fullrun.py --voice ~/Workspace/documentary-voice \
  --model ~/Workspace/voice-studio/.runtime/data/models/qwen3-tts-1.7b-base-bf16 \
  --lua-python <lua> --tag zhCN-1.5.0-1 >> work/fullrun.log 2>&1 &
echo $! > work/fullrun.pid
```

Then queue the complete stories and the quest/recap/book pages behind it (same tag):

```
nohup caffeinate -is <mlx> scripts/storyrun.py --voice ~/Workspace/documentary-voice \
  --model ~/Workspace/voice-studio/.runtime/data/models/qwen3-tts-1.7b-base-bf16 \
  --lua-python <lua> --tag zhCN-1.5.0-1 --after $(cat work/fullrun.pid) >> work/storyrun.log 2>&1 &
```

fullrun.py takes each finished batch, records only the `pending` clips (about 70–80 an hour), and creates the release with
every pack, then refreshes it each time another pack is complete; storyrun.py does the same for its part. It stops when nothing is left; `work/fullrun.log`
says if any clip still has no translation. Clips whose speaking rate looked wrong three times are marked `check` and
left out (`python3 scripts/update.py status`).

Then commit `translations/`, `glossary/`, `manifest/` and the `CORE_VERSION` change (never `addons/`, `work/` or
audio), and say in the release notes which Lore Forever version it is for.

The voice, model, settings and the recording rules are the same as the first run: see REPORT.md. Don't swap the TTS
model or voice for an update, or old and new stories will sound different.
