# 任务说明：为 Lore Forever 制作简体中文语言包 + 中文女声语音包

> 给在另一台电脑上工作的 Claude。仓库主人（用户）要你按这份说明制作，然后把结果上传到本仓库。
> 另一台电脑（用户的游戏电脑）上的 Claude 会下载并部署你的结果，所以**格式必须和插件完全兼容**。

## 1. 目标

Lore Forever 1.3.0 是 WoW: Forever 的剧情插件（CurseForge 项目 1715510），自带英文女声旁白。
要做的是：

1. 一个**简体中文语言包** `LoreForever_Lang_zhCN`：把所有有旁白的剧情文本（以及界面文字）翻译成中文。
2. 一套**中文女声语音包**：用用户的 AI 女声（就在这台电脑上，见用户给你的声音说明/模型）把**所有英文女声旁白**用中文重新录一遍。

用户的游戏客户端是英文的（`textLocale enUS`），他会在插件设置里把插件语言切成简体中文。

## 2. 输入材料

**从 CurseForge 获取**：在这台电脑上用 CurseForge 安装 **Lore Forever 1.3.0**（项目 1715510），以及它的这些可选下载：

- 女声：`LoreForever_Voice_Female`、`_Alliance`、`_Horde`、`_MoreItems`、`_MorePeople`、`_MorePlaces`、`_Quests`、`_Quests2`、`_Quests3`、`_MoreQuests1`、`_MoreQuests2`、`_MoreQuests3`
- 法语参考：`LoreForever_Lang_frFR`、`LoreForever_Voice_Female_MorePeople_frFR`

不需要装 WoW 本体，只要这些插件文件夹（CurseForge 装好后找到它们的文件夹，复制到工作目录 `addons/` 下）。其中：

| 文件夹 | 用途 |
|---|---|
| `LoreForever/` | 插件核心：代码 + `Data/` 英文剧情数据 |
| `LoreForever_Lang_frFR/` | 法语语言包，**中文语言包的模板** |
| `LoreForever_Voice_Female*/` | 每个包的 `.toc`、`Clips.lua`、`Transport.lua`/`.json`：片段 ID、英文文字、分段方式；`Audio/` 里的 MP3 用来对齐音频格式 |
| `LoreForever_Voice_Female_MorePeople_frFR/` | 非英语女声包的现成例子 |

先核对版本：`LoreForever/LoreForever.toc` 的 `## Version` 必须是 `1.3.0`。用户那边的片段数是（`Clips.lua` 里 `c["..."]` 的行数）：
Female 198、Alliance 385、Horde 296、MoreItems 2435、MorePeople 2500、MorePlaces 2392、Quests 4104、Quests2 3535、Quests3 4709、MoreQuests1 3688、MoreQuests2 5261、MoreQuests3 1953，合计 31,456。对不上就是版本不同，先告诉用户。

**这些材料是插件作者的作品，不要提交到本仓库**（本仓库是公开的）。

## 3. 先读懂插件的格式（必须）

插件没有附带它的构建工具（`pipeline/lore/compile_lua.py`、`voicepack.py`），所以格式要从代码和现成的包里读出来。先读：

- `Packs.lua` 开头的说明：包的类型、toc 字段（`X-LoreForever-Pack/Locale/Format/DataVersion/Extends/Gender/Sample`）、`P.clips`、`P.len`（十分之一秒）。
- `Lang.lua`：语言包怎么合并进 `ns.DB`，`clipHash` / `answerHash` / `fullclips` 怎么用来校验录音和文字是否一致（约 778 行起），`MarkUntranslated`。
- `Voice.lua`：`Voice.KeyOf` / `Voice.InLanguage`（带语言后缀的语音包怎么替代原声）、`Voice.Resolve`、Transport（长篇分段）、任务对话包的 `P.questVoice` / `P.questText` / `P.questTitle`（约 2518–2760 行）。
- `LoreForever_Lang_frFR/`：每个文件的结构，中文包照这个做。
- `LoreForever_Voice_Female_MorePeople_frFR/`：一个已存在的"非英语女声包"，中文语音包照这个做（注意它的 `Extends` 写的是谁）。

**关键：哈希。** 录音只有在 `语音包 Clips.lua 的 c[id]` 等于 `语言包的 clipHash[id]` 时才会播放，而 `clipHash` 必须是插件期望的、对该段文字算出来的值。
找出哈希的算法（在核心代码里找 `clipHash`、`hash(`、`fullHash` 的计算方式；`Transport.lua` 里有 `hash` / `fullHash`），
然后**先用法语包验证**：从 `LoreForever_Lang_frFR` 的文字重新算出它的 `clipHash`，必须和包里现有的值 100% 一致，才能用在中文上。
如果算法在 Lua 里找不到（可能只在作者的 Python 构建脚本里），就从现有数据反推并写清楚依据；反推不出来就停下，在 `REPORT.md` 里说明并告诉用户。

## 4. 要交付的包

全部是独立的插件文件夹，名字**按插件的命名约定**（如下）：

1. `LoreForever_Lang_zhCN`：照 `LoreForever_Lang_frFR` 的文件结构：
   - toc：`X-LoreForever-Pack: lang`、`X-LoreForever-Locale: zhCN`、`X-LoreForever-Format: 1`、`X-LoreForever-DataVersion`（写核心数据的版本，见 `Data/` 和 frFR toc）、`X-LoreForever-LanguageName: 简体中文`，`Dependencies: LoreForever`，`LoadOnDemand: 1`。
   - `UI.lua`（界面文字）、`Entries*.lua`（剧情文本）、`Names.lua`（**国服官方中文名**：地名、NPC、物品、任务，名字要和国服客户端一致）、`Search_*.lua`（中文的搜索索引，注意 `Packs.lua` 里 zhCN 是 `han` 文字，分词方式要看核心怎么用这个索引）、`Clips.lua`（`clipHash`，按第 3 节的算法）。
2. 女声语音包，**镜像英文女声那一套的拆分**，每个加 `_zhCN` 后缀：

   | 英文包 | 中文包 |
   |---|---|
   | `LoreForever_Voice_Female` | `LoreForever_Voice_Female_zhCN` |
   | `LoreForever_Voice_Female_Alliance` / `_Horde` | `..._Alliance_zhCN` / `..._Horde_zhCN` |
   | `..._MoreItems` / `_MorePeople` / `_MorePlaces` | 各自加 `_zhCN` |
   | `..._Quests` / `_Quests2` / `_Quests3` | 各自加 `_zhCN` |
   | `..._MoreQuests1` / `2` / `3` | 各自加 `_zhCN` |

   合计 31,456 个片段（第 2 节的数字）。`LoreForever_Voice_Default*`（男声）的片段 ID 和女声相同，**不用做**。
   每个包：toc（`Pack: voice`、`Locale: zhCN`、`Gender: female`、该有的 `Extends`，照 frFR 包）、`Clips.lua`（`c[id] = hash`、`P.len[id]`）、需要分段的长篇写 `Transport.lua`（结构照英文包：`hash`、`fullHash`、各段 `file`/`duration`/`start`/`head`）、`Audio/`、`CREDITS.txt`。
   任务对话包：客户端是英文，中文录音要走"在英文任务页上播放中文录音 + 中文字幕"那条路（`P.questVoice`、`P.questText`、`P.questTitle`），按 `Voice.lua` 的规则写。

## 5. 翻译要求

- 自然、口语化、适合朗读的简体中文，不是逐字翻译。
- 专有名词一律用**国服官方译名**，建一份 `glossary/zhCN.tsv`（英文 → 中文）全程统一，查不到官方名的标出来。
- 只翻译文字，不改 ID、键名、链接、格式代码（`|c...|r` 等）。
- 文字来自 Warcraft Wiki，CC BY-SA 4.0：中文包的 `CREDITS.txt` 要保留出处并写明是翻译。

## 6. 录音要求

- 用用户的 AI 女声。用英文女声包 `Audio/` 里的 MP3 量出参数（采样率、声道、码率），中文包用同样的。
- 统一响度（和英文样本听感一致，例如都归一到约 -16 LUFS），去掉首尾多余静音。
- 长篇按英文 Transport 的方式分段，`duration`/`start` 用实际音频时长。
- 每个片段写 `P.len`（十分之一秒，取实际时长）。

## 7. 做法

1. **先做试点再全量。** 先只做 `zone:stormwind`（`X-LoreForever-Sample`）和大约 30 个人物 / 物品 / 任务片段，打成同样结构的包，发一个 `pilot-1` Release（见第 8 节），然后**停下，告诉用户在游戏里试听**。用户确认没问题再做全量。
2. 全程可中断续做：`manifest/clips.jsonl`，每行一个片段：`id`、所属包、英文原文的哈希、中文文字、`clipHash`、音频文件、时长、状态。插件以后更新英文，只要重做英文哈希变了的片段。
3. **自检**（用 Lua 5.1 或 lupa 写一个校验脚本放 `scripts/`）：用一个假的 `LoreForeverPacks.Begin` 把所有生成的包加载一遍，检查：每个语音片段在语言包里都有相同的 `clipHash`；音频文件都存在；`P.len` 都有；Transport 的分段文件都在；toc 字段齐全。结果写进 `REPORT.md`。

## 8. 交付到本仓库

本仓库：`https://github.com/szh101/lore-forever-voice`（公开）。

- **提交到仓库**：`scripts/`、`glossary/`、`manifest/`（不含音频）、`REPORT.md`（做了什么、片段数、没做到或不确定的地方、哈希是怎么验证的）。
- **音频和包不进 git**（文件太大）：每个插件文件夹打一个 zip，作为 **GitHub Release 附件**上传（单个附件 < 2 GB，超了就把包按 `Audio/` 子目录拆成 `.part1.zip`、`.part2.zip`）。
  同一个 Release 里放 `release-manifest.json`：每个 zip 的文件名、对应的插件文件夹、大小、`sha256`，以及插件核心版本 `1.3.0`。
  Tag 用 `pilot-1`、之后 `zhCN-1.3.0-1`、`zhCN-1.3.0-2`…
- 不要提交 `addons/` 参考材料、英文音频、任何密钥或个人信息。提交用 GitHub noreply 邮箱。

## 9. 部署（游戏电脑那边做，你不用做）

游戏电脑上的 Claude 会：下载 Release、校验 `sha256`、把文件夹放进
`World of Warcraft\_forever_\Interface\AddOns\`，并在 `D:\games\LoreForever-zhCN\` 留一份备份。
这些文件夹不属于任何 CurseForge 项目，所以 CurseForge 更新 Lore Forever 时不会删除或覆盖它们。
只有插件改了英文文字的那些片段会失效（插件自己会跳过不匹配的录音），到时用 manifest 增量重做即可。
