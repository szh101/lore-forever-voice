# Install the Chinese narration on the gaming PC (for the Claude on Windows)

The owner keeps Lore Forever's **text in English** and wants the stories **narrated in Chinese**. These packs are a
separate narrator, "Lore Forever Chinese female narrator" (`LoreForever_Voice_ChineseFemale` and the packs that
extend it). They need Lore Forever itself (CurseForge) and nothing else; there is no language pack to install, and
the add-on's language setting stays English.

1. Pick the release: the newest tag (`pilot-1` first; later `zhCN-1.4.0-1`, ...).
   `gh release view <tag> --repo szh101/lore-forever-voice` and `gh release download <tag> --repo
   szh101/lore-forever-voice --dir <a new empty folder>` (the repo is private; the owner is signed in to gh).
2. Verify every zip against `release-manifest.json` (`sha256`, `size`). Stop and tell the owner on any mismatch.
3. Close the game (or be ready to `/reload`). Unzip each zip into
   `World of Warcraft\_forever_\Interface\AddOns\` (each zip holds one folder; a `.partN.zip` set all goes into the
   same folder). Replace an older copy of the same folder completely (delete it first), so no stale MP3s remain.
4. Keep a copy of the zips and `release-manifest.json` in `D:\games\LoreForever-zhCN\<tag>\`.
5. Don't touch the CurseForge-managed folders (`LoreForever`, `LoreForever_Voice_*` without `ChineseFemale`). These
   folders aren't part of any CurseForge project, so CurseForge updates leave them alone.
6. Tell the owner what to do in the game:
   - Log in (or `/reload`). Lore Forever says in chat that a new voice was found, at the bottom of the narrator list.
   - Open Lore Forever's Options > Narration voices and move **Lore Forever Chinese female narrator** to the top
     (tick it if it isn't ticked). The other narrators fill in the stories it hasn't recorded.
   - Test with Stormwind City (the sample), Goldshire, Hogger, the quest "Wanted: Hogger", and Bartleby's Mug.
   - If the subtitles show boxes instead of Chinese, switch subtitles off in the ⋯ menu ("Show subtitles"). That's
     only the display; the narration plays either way.
