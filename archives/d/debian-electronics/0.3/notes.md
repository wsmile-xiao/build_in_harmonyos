# debian-electronics 0.3 — 适配笔记

## 概述
Debian Pure Blend（Debian Electronics，电子设计软件选集）。真实身份：**不是库**——一个 native
源包生成 **15 个 `Architecture: all` 纯元包**（`electronics-tasks` tasksel 描述包 +
`electronics-all` 总览元包 + 13 个 `electronics-<topic>` metapackage）。零编译产物、零可执行文件；
"内容" = 13 个 Deb822 任务文件 + genblends 生成的 tasksel desc + 15 个 dpkg 依赖选择声明。

## 真实身份 / 源
- salsa: https://salsa.debian.org/blends-team/electronics（sid 当前源版本 = 0.3）
- 源: pool `debian-electronics_0.3.tar.xz`（native，Format 3.0）
- sha256 `0b991e5cf4e9ad3006d5b1560b2aa52f4b9249d6de44516eb322e37f3dc369d8`
  （本地 sha256sum 实测，与官方 `.dsc` 的 `Checksums-Sha256` 一致）
- Build-Depends-Indep: `blends-dev (>= 0.7~)`。顶层 `Makefile` 与 `debian/rules` 各只有一行
  `include /usr/share/blends-dev/...`，须在 Debian 环境（apt 可用性过滤）由 genblends 生成 control。

## 实测形态（本地解压清点，26 文件）
```
文件总数        : 26
C/C++ 源码      : 0      (find -name '*.c|*.cpp|*.h' -> 0)
测试文件        : 0      (find -iname '*test*' -> 0；ctest/pytest 注册 = 0)
tasks/          : 13 个 Deb822 任务文件（analog/asic-dev/cad-gui/digital/doc/dsp-dev/
                   fpga-dev/gadgets/measurements/microcontrollers/pcb/radio-dev/simulation）
dependency_data : 2 个历史快照 JSON（0.1、0.2）—— 注意：0.3 源树**没有** 0.3 快照
debian/control  : 15 个 Package: 声明，全部 Architecture: all，全部 electronics-* 前缀
desc            : 14 段落 / 14 个 Task: / 13 个 Key:（父任务 debian-electronics 无 Key）
Install: 分布   : 13 true / 0 false
Format: 头      : 13/13 全部带 `Format: https://blends.debian.org/blends/1.1`（**新格式**）
文件级 Depends  : 无（0 个任务文件有 Depends: 字段）
快照 0.2 键     : 13（与 tasks/ 文件集合完全一致）
快照去重引用    : 109 条 OS 包名
```

### 集合关系（**非 1:1**，如实记录）
| 关系 | 数量 | 明细 |
|---|---|---|
| control 有包、tasks 无文件 | 2 | `electronics-all`、`electronics-tasks` |
| tasks 有文件、control 无包 | 0 | 13 个 topic 全部有对应 electronics-<topic> 元包 |
| desc 有 Key、tasks 无文件 | 0 | 13 个 Key 全部映射到已打包任务文件 |
| 快照键 vs tasks 文件 | 0 差 | 13 == 13 |

## 与 debian-science 1.15 的关键差异（同族不同格式）
1. **task 文件是新 blends 1.1 格式**（每个文件都有 `Format:` 头），因此**没有**旧格式
   `Depends: -> Recommends:` 降级规则；文件级 `Recommends:`/`Suggests:` 直接映射到元包
   同名字段。debian-science 的旧格式降级语义在此**不适用**（registry.semantics.task_format 如实记录）。
2. **genblends apt 可用性过滤仍存在**：部分任务文件 `Recommends:` 中的包在生成 control 时
   被降级为元包 `Suggests:`（共 9 个 topic 元包有降级；实测 analog 的
   `gwave`/`qucs` 从任务 Recommends -> 元包 Suggests）。registry.demotions 逐包记录。
3. **快照**：debian-science 1.15 源树带 1.15 快照；本包 0.3 源树只有 0.1/0.2 快照，
   **没有 0.3 快照**（上游在 0.3 发布时未更新 dependency_data）。故打包最新可用快照 0.2，
   并在 notes/MANIFEST/registry.semantics 如实披露。

## Conan 建模（单 metadata/registry 包，零伪造）
- 单 recipe `debian-electronics/0.3`，data/metadata（`package_type="unknown"`）；
  package() 装真实产物：
  - `share/debian-electronics/tasks/*`（13 个原文，未改写）
  - `share/debian-electronics/tasksel/debian-electronics-tasks.desc`（源树 genblends 产物原文）
  - `share/debian-electronics/dependency_data/debian-electronics_0.2.json`（官方快照原文，
    0.3 无新快照，此为最新可用）
  - `share/debian-electronics/registry.json`（build() 纯解析派生，见下）
  - `licenses/copyright`
- **零 Conan requires**：control/snapshot 中的引用全部是 OS/distro 包选择（metadata-only）。
  机械复制进 requires 会造出虚假且不可满足的依赖图 → 禁止。conan requires 列表为空。
- `registry.json` 内容：13 个 task 条目（Task/Description/Install/Format/file_recommends/
  file_suggests）、14 个 desc 段落名、13 个 Key、15 个 control 包声明（含解析模板后的
  Depends/Recommends/Suggests/描述摘要）、9 个 apt 降级记录、快照主题集合与去重引用计数、
  `semantics` 块。
- `debian/control` 模板解析：`${source:Version}` -> `0.3`，`${misc:Depends}` -> 空
  （与官方 .deb 的 control 实测一致，见下）。每个 topic 元包 Depends: `electronics-tasks (= 0.3)`；
  `electronics-tasks` Depends: `tasksel`；`electronics-all` Recommends 全部 13 个 topic 元包。
- 不装 0.1 快照（避免被误读为当前依赖），只装最新 0.2。
- 无 `commands.json`：非 CLI，无 bin/ 产物（R38 不适用）。

## 与官方 .deb 交叉核验（诚实边界证据）
本地下载 `electronics-all/analog/microcontrollers/tasks` 四个 0.3 版 `_all.deb` 实测：
- 每个 metapackage .deb 本体只含一个标题文件
  `/usr/share/blends/tasks/electronics/<topic>`（内容 = task 的 `Task:` 标题，
  如 analog = `Analog design`）+ doc；`electronics-tasks.deb` 含
  `/usr/share/tasksel/descs/debian-electronics-tasks.desc`（与源树 desc **逐字节一致**）。
- `electronics-analog_0.3_all.deb` control 实测：`Depends: electronics-tasks (= 0.3)`、
  `Recommends: gnucap, magic, ngspice, qsapecng, simulide`、`Suggests: gwave, python3-gnucap, qucs`
  ——与源 control（模板解析后）完全一致，证实 `${misc:Depends}` 展开为空、降级语义成立。

## 测试
- **上游**：无（无 autopkgtest / CI / test 目录；清点证据见 test_package/MANIFEST.yml
  的 `upstream_test_evidence`）。upstream 0/0。
- **Harmony 特有 package/data 验证**：`test_package/`（消费者测试）
  - `test_debian_electronics.py`：layout / tasks Deb822 字段（新格式 Format: 头）/
    desc 结构 / registry 交叉复核 / control 15 包声明与依赖模板解析结果 /
    官方快照集合与命名规范 / 新格式语义 + apt 降级 + conan_requires==none —— 共 **40 项断言**
  - `test_package/conanfile.py`：`self.run("python3 <script> <package_folder>")` 实际执行

## 诚实边界（保留）
- 本包**不**翻译任何 Debian 依赖为 Conan requires（见上）。
- 本包**不**制造假 `.so` / 假 executable；**不**声称能安装完整 Debian Electronics 选集。
- 0.3 无官方依赖快照（只有 0.1/0.2），打包 0.2 并在 semantics/notes 披露，不伪造 0.3 快照。
- 9 个 apt 降级为上游事实（任务文件 Recommends vs 元包 Suggests 的差异），如实记录而非抹平。
- 快照 references 是 Debian 包名（非 Conan 包名），仅作为元数据记录。

## 与既有知识的关系
同族先例（Debian Pure Blend 类）：
`archives/d/debichem/0.0.12`（13 元包）、`archives/d/debian-parl/1.9.33+nmu1`（5 元包）、
`archives/d/debian-science/1.15`（45 元包，**旧格式** task 文件）。本条为**新 blends 1.1 格式**
变体（15 元包 / 13 tasks / 14 desc 段落 / 无 0.3 快照 / 109 引用 / 9 个 apt 降级），
知识增量 = 新格式语义记录 + apt 可用性降级的逐包记录 + 快照缺失的诚实披露。
通用方法见 knowledge/drafts/DRAFT-debian-pure-blends-metapackage-to-conan-metadata-registry.md。

## R47 语言预检记录
`lang-preflight debian-electronics 0.3 --src <src>` → `detected_language=c`、exit 0
（`expected=cpp`，c↔cpp 兼容族）。原因为检测器按"构建系统优先"路径将顶层 Makefile
（仅 include blends-dev + 零可统计源文件）归入 c/cpp 族。
本包实际为纯打包元数据，按 metadata/registry 包路线适配（非 C/C++ 编译，也不硬做空壳）。
