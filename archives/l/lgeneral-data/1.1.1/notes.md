# lgeneral-data 1.1.1 适配笔记

## 概述

把 LGeneral（开源一战题材回合制战略游戏）的免费内容包 **k.u.k General** 适配为
HarmonyOS PC 的 Conan 纯数据包。这是 LGeneral 本体（`archives/l/lgeneral`）运行所
必需的资产包：没有它，游戏只有引擎、没有单位/国家/地图/剧本。

## 上游形态

上游是 Debian 源码包（内容包本身按上游 README 直接分发目录树）：

```
lgeneral-data-1.1.1/
├── campaigns/kukgen                        战役定义（5209 字节）
├── scenlist                                剧本清单（22 个剧本名，* 表示不属于战役）
├── gfx/flags/kukgen.bmp                    旗帜（1）
├── gfx/units/kukgen{,_attack,_guard,_move,_strength}.bmp   单位贴图（5）
├── gfx/terrain/kukgen/*.bmp                地形贴图（53）
├── maps/kukgen/                            地图（61 个）+ maps/kukgen.tdb 地面表
├── nations/kukgen.ndb                      国家表（18 个段落 / 38 个字段行）
├── units/kukgen.udb                        单位表（980 个段落 / 11803 个字段行）
├── scenarios/kukgen/                       剧本（22 个）+ .order 顺序文件
├── sounds/kukgen/*.wav                     音效（8）+ sounds/LICENSE.sounds
├── docs/                                   5 个转换/说明文档
└── COPYING / LICENSE / README / BUGS/ THANKS / TODO / ChangeLog
```

`gfx/` 下合计 **59 个 BMP**，`sounds/` 下 **8 个 WAV**。

## 安装内容

按上游 README 的原话安装：

> "Copy the directories campaigns, gfx, maps, nations, scenarios, sounds and units
>  to your LGeneral data directory (e.g. `/usr/share/games/lgeneral`)"

即把 7 个目录 + `scenlist` 装到 `share/games/lgeneral/`（只把 `/usr/share` 换成
Conan 的 `share/`），文档装到 `share/doc/lgeneral-data/`，三份许可证收集到
`licenses/`。消费方通过 `LGENERAL_DATA_DIR`（buildenv/runenv）或
`cpp_info.resdirs` 定位。

## 为什么没有编译步骤

内容包全是最终资产（BMP/WAV/文本表），上游没有构建系统，Debian 侧 `debian/rules`
也只做拷贝。因此配方：

- `package_type = "unknown"`，不声明 `settings`（纯数据包，产物与架构无关）；
- `build()` 只做数据完整性自检（含 `scenlist` ↔ `scenarios/kukgen/` 交叉校验），
  不调用任何编译器/构建系统；
- 不创建 `commands.json`、不伪造二进制测试（E255 的 forbid_1）。

## 上游测试情况

上游没有测试目录、测试框架或 CI 测试阶段；Debian 侧也没有 autopkgtest。
**上游用例数 N = 0。**

## 新增自检（test_package/test_lgeneral_data.py，35 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 数据目录齐备 | 7 | 上游 README 点名的 7 个目录逐个检查"存在且非空" |
| 剧本清单一致性 | 5 | `scenlist` 存在；列出 22 个剧本；**每个剧本在 `scenarios/kukgen/` 里都存在**；`.order` 点文件被保留；条目数 = 22 + 1 |
| 贴图 | 7 | `gfx/` 下 59 个 BMP；全部有合法 `BM` 魔数与位图头；地形 53；单位 5；旗帜 1 |
| 音效 | 3 | 8 个 WAV；全部为合法 `RIFF…WAVE`；`LICENSE.sounds` 随包发布 |
| 地图与战役 | 3 | `maps/kukgen/` 61 个文件；`kukgen.tdb` 存在；`campaigns/kukgen` 非空 |
| 单位表 / 国家表 | 6 | 表格存在；以 `@` 开头；字段行用单字节 `0xBB` 分隔 key/value 且两侧非空；含 `<section` 段落与 `>` 结束符 |
| 文档与纯净性 | 4 | `docs/` 5 个文件；安装目录只有 7 目录 + `scenlist`；`licenses/` 三份许可证 |

三个最关键的断言：

1. **`scenlist` ↔ `scenarios/kukgen/` 逐条核对**：少一个剧本文件 = 玩家在游戏里
   点开那一场战役必然失败，而"目录里有 23 个文件"这种断言发现不了。
2. **`.order` 点文件必须被拷出来**：Conan 的 `copy(self, "*", ...)` 在部分版本下
   不覆盖以 `.` 开头的文件（与 `ieee-data` 的 `.lastupdate` 同类问题）。丢了它
   剧本顺序就没了。
3. **BMP/WAV 逐文件魔数校验**：59 + 8 个资产逐个验证容器头，避免"文件在但内容被
   截断"。

## 两个踩过的坑（已修）

1. `copy(self, "*", src=<dir>, dst=data_dir)` 复制的是 src 的**内容**，会把
   `maps/kukgen` 直接铺成 `lgeneral/kukgen` 并与其他目录冲突（`FileExistsError`）。
   正确写法是 `dst=os.path.join(data_dir, name)`。
2. `.ndb/.udb` 的 key/value 分隔符是**单字节 0xBB**，不是 Tab。用
   `encoding="utf-8", errors="replace"` 读会把 0xBB 变成 U+FFFD 导致匹配失败，
   必须用 `latin-1` 读。

## 构建与验证

```bash
conan create archives/l/lgeneral-data/1.1.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
python3 scripts/ohc-run.py conan-verify lgeneral-data 1.1.1
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/l/lgeneral-data/lgeneral-data_1.1.1.orig.tar.gz`
  （官方路径 `https://deb.debian.org/debian/pool/main/l/lgeneral-data/lgeneral-data_1.1.1.orig.tar.gz`）
- SHA256: `35735288fcb6000acf0c0eb335974e51c774a9bf724efa39ce4c6fd4e242c2dc`
  （与 `lgeneral-data_1.1.1-1.dsc` 的 `Checksums-Sha256` 一致）
- License: CC-BY-SA-3.0（内容部分）+ GPL（复制来的 `COPYING` 工具链文本）

---

**编译结束**: 2026-09-19
**最终状态**: built
