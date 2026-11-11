# Lore Forever 中文女声旁白 · Chinese narration for Lore Forever

为 WoW: Forever 插件 [Lore Forever](https://www.curseforge.com/wow/addons/lore-forever)（CurseForge 1715510，作者
mikeliudev）录制的中文女声旁白。插件文字保持英文，剧情用中文朗读，字幕显示中文旁白稿。
做成一位独立的旁白 "Lore Forever Chinese female narrator"（`LoreForever_Voice_ChineseFemale` 及其扩展包），
不需要语言包，适用于 Lore Forever 1.3.0 和 1.4.0。

Chinese (Mandarin) narration for the Lore Forever add-on: a separate narrator that reads the lore in Chinese over the
add-on's English text. Not an official Lore Forever pack.

## 下载和安装 · Install

1. 在 [Releases](../../releases) 下载最新的 `zhCN-…` 版本里所有 zip（`release-manifest.json` 里有每个文件的 sha256）。
2. 解压到 `World of Warcraft\_forever_\Interface\AddOns\`，每个 zip 是一个文件夹；更新时先删掉旧的同名文件夹。
3. 进游戏（或 `/reload`），打开 Lore Forever 的 Options > Narration voices，把
   **Lore Forever Chinese female narrator** 移到最上面。没录到的故事会由下一位旁白来读。
4. 如果字幕显示成方框，在 ⋯ 菜单里关掉字幕，旁白照常播放。

详细步骤（也适合交给 AI 助手执行）：[INSTALL.md](INSTALL.md)。

## 内容 · What's in it

9 个剧情包里的 5,165 段概述旁白：地点、人物、物品和任务故事。任务对话（`_Quests*`）还没有做。
制作方法、哈希验证、版本兼容和已知问题：[REPORT.md](REPORT.md)。

插件作者更新后怎么补新内容的语音 · After a Lore Forever update: [UPDATING.md](UPDATING.md)。

## 授权 · License

- 剧情文字来自 Lore Forever，改编自 [Warcraft Wiki](https://warcraft.wiki.gg)，按
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 授权。中文旁白稿（`translations/`、`glossary/`）
  和录音都是它的演绎作品，同样按 **CC BY-SA 4.0** 授权：署名 "Chinese narration by szh101"，相同方式共享。
- 声音完全由 AI 合成（Qwen3-TTS），不是真人的声音。
- `scripts/` 和 `tests/` 里的代码按 MIT 授权（见 [LICENSE](LICENSE)）。
- 欢迎 Lore Forever 的作者把这些旁白收进插件或官方语音包。
- World of Warcraft 和 Warcraft 是暴雪娱乐的商标。Lore Forever 和本项目都是粉丝作品，与暴雪无关。
