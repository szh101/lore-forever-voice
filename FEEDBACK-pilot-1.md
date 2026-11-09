# pilot-1 feedback — approved, go ahead with the full run

From the gaming PC, 2026-11-08. The owner tested pilot-1 in game and approved it.

## Result

- **Approved.** The owner says the Chinese narration sounds very good. Go ahead with the full run of the 9 lore packs
  (the ~5,165 overview clips in REPORT.md, "Full run"), same voice, same settings, same pack layout.
- Quest giver dialogue (`_Quests*`) stays a separate later step; not part of this run.

## What was installed and checked on the gaming PC

- Lore Forever core on the gaming PC is **1.3.0** (CurseForge hadn't updated it to 1.4.0 yet). The 1.3.0
  `Voice.ScopedClip` has the same rule (scopedVersion 1, `row.hash == P.clips[id]`, entry must exist, pack locale must
  match the reading language), and all 32 pilot ids exist in 1.3.0's data. The packs worked on 1.3.0.
- All 5 zips matched `release-manifest.json` (sha256 and size); each holds only its own folder; Clips.lua is data only.
- Installed into `_forever_\Interface\AddOns\`, copies kept in `D:\games\LoreForever-zhCN\pilot-1\`.

## Issue to look at

- **The narrator is missing from `/lore options` > Narration voices.** The ordered list in the options window doesn't
  show "Lore Forever Chinese female narrator". `/lore voice` lists it and `/lore voice <n>` put it first, and that
  works, so playback is fine. Please check whether something in the packs (toc fields, `X-LoreForever-Credit`,
  `Locale: enUS` with Chinese text, the Extends packs, etc.) keeps the options list from showing it, comparing with how
  Options.lua builds that list in 1.3.0 and 1.4.0. If it's the add-on's own behaviour, say so in REPORT.md; don't
  change anything that would make the packs depend on 1.4.0.

## For the full run

- Keep the packs working on both **1.3.0 and 1.4.0** (the gaming PC may update at any time): only use ids that exist in
  both, or note in REPORT.md which ones need 1.4.0.
- Release as `zhCN-1.4.0-1` with the same zip-per-folder layout and `release-manifest.json`; split any zip over 2 GB
  into parts as INSTRUCTIONS.md says. Partial releases while the run is in progress are fine (e.g. one pack at a time).
- Correction to INSTRUCTIONS.md: the per-pack clip counts add up to 31,456, not 35,456 (as REPORT.md noted).
- Proper nouns: the owner will report any that sound wrong; until then keep using `glossary/zhCN.tsv` consistently.
