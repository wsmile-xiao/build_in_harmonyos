# debian-science 1.15 — 适配笔记

## 概述
Debian Pure Blend（Debian Science，科学研究软件选集）。真实身份：**不是库**——一个 native
源包生成 **45 个 `Architecture: all` 纯元包**（`science-tasks` tasksel 描述包 +
`science-config` 配置包 + `science-all` 总览元包 + `science-electronics` 过渡元包 +
41 个 `science-<topic>` metapackage）。零编译产物、零可执行文件；"内容" = 46 个 Deb822
任务文件 + genblends 生成的 tasksel desc + 45 个 dpkg 依赖选择声明。

## 真实身份 / 源
- salsa: https://salsa.debian.org/blends-team/science（sid 当前源版本 = 1.15）
- 源: pool `debian-science_1.15.tar.xz`（native，Format 3.0）
- sha256 `79866833c4c1d2ef553d5e1b9879155d6b4171fae1ac03eda7747e84517eb768`
  （实测与官方 `.dsc` 的 `Checksums-Sha256` 一致）
- Build-Depends-Indep: `blends-dev (>= 0.7.5~)`；Build-Depends: `debhelper-compat (= 13)`。
  顶层 `Makefile` 与 `debian/rules` 各只有一行 `include /usr/share/blends-dev/...`，
  须在 Debian 环境（apt 可用性过滤）由 genblends 生成 control。

## 实测形态（本地解压清点，97 文件）
```
文件总数        : 97
C/C++ 源码      : 0      (find -name '*.c|*.cpp|*.h' -> 0)
测试文件        : 0      (find -iname '*test*' -> 0；ctest/pytest 注册 = 0)
tasks/          : 46 个 Deb822 任务文件
dependency_data : 38 个历史快照 JSON (0.1 -> 1.15)
debian/control  : 45 个 Package: 声明，全部 Architecture: all，全部 science-* 前缀
desc            : 42 段落 / 42 个 Task: / 41 个 Key:（父任务 debian-science 无 Key）
Install: 分布   : 18 true / 28 false
Metapackage:    : 仅 bci/devices/tools 3 文件出现，均为 false
快照 1.15 键    : 46（与 tasks/ 文件集合完全一致）
快照去重引用    : 1976 条 OS 包名
```

### 集合关系（**非 1:1**，如实记录）
| 关系 | 数量 | 明细 |
|---|---|---|
| control 有包、tasks 无文件 | 4 | `science-all`、`science-config`、`science-electronics`、`science-tasks` |
| tasks 有文件、control 无包 | 5 | `bci`、`devices`、`neuroscience-datasets`、`social`、`tools` |
| desc 有 Key、tasks 无文件 | 0 | 41 个 Key 全部映射到已打包任务文件 |
| 快照键 vs tasks 文件 | 0 差 | 46 == 46 |

## Conan 建模（单 metadata/registry 包，零伪造）
- 单 recipe `debian-science/1.15`，data/metadata（`package_type="unknown"`）；
  package() 装真实产物：
  - `share/debian-science/tasks/*`（46 个原文，未改写）
  - `share/debian-science/tasksel/debian-science-tasks.desc`（源树 genblends 产物原文）
  - `share/debian-science/dependency_data/debian-science_1.15.json`（官方快照原文）
  - `share/debian-science/registry.json`（build() 纯解析派生，见下）
  - `licenses/copyright`
- **零 Conan requires**：1976 条引用全部是 OS/distro 包选择（metadata-only）。
  机械复制进 requires 会造出虚假且不可满足的依赖图（Debian 包名 ≠ Conan 包名；且多为
  OS/桌面级包）→ 禁止。conan requires 列表为空。
- `registry.json` 内容：46 个 task 条目（Task/Description/Install/Metapackage/
  file_depends/file_recommends/file_suggests + 降级后的 metapackage 语义）、
  42 个 desc 段落名、41 个 Key、45 个 control 包声明（含 Architecture/依赖/描述摘要）、
  快照主题集合与去重引用计数、`semantics` 块。
- **旧格式 blends 语义**（实测 .deb 印证）：task 文件无 `Format:` 头 → 文件级 `Depends:`
  在元包中降级为 **Recommends**；`Suggests:` → **Suggests**；每个元包另
  `Depends: debian-science-tasks (=1.15)`。该映射写入 registry.semantics，供消费者还原
  Debian 语义。
- 不装 37 份历史快照（避免被误读为当前依赖），只装 1.15。
- 无 `commands.json`：非 CLI，无 bin/ 产物（R38 不适用）。

## 测试
- **上游**：无（无 autopkgtest / CI / test 目录；清点证据见 test_package/MANIFEST.yml
  的 `upstream_test_evidence`）。upstream 0/0。
- **Harmony 特有 package/data 验证**：`test_package/`（消费者测试）
  - `test_debian_science.py`：layout / tasks Deb822 字段 / desc 结构 / registry 交叉复核 /
    control 45 包声明 / 官方快照集合与命名规范 / semantics —— 共 **33 项断言**
  - `test_package/conanfile.py`：`self.run("python3 <script> <package_folder>")` 实际执行

## 诚实边界（保留）
- 本包**不**翻译任何 Debian 依赖为 Conan requires（见上）。
- 本包**不**制造假 `.so` / 假 executable；**不**声称能安装完整 Debian Science 选集。
- 4/5 个集合差异（见上表）为上游事实，如实披露而非抹平。
- 快照 references 是 Debian 包名（非 Conan 包名），仅作为元数据记录。

## 与既有知识的关系
同族先例（Debian Pure Blend 类）：
`archives/d/debichem/0.0.12`（13 元包）、`archives/d/debian-parl/1.9.33+nmu1`（5 元包），
通用方法见 Issue #2884 对应的 draft。本条为其**大规模变体**
（45 元包 / 46 tasks / 42 desc 段落 / 38 快照 / 1976 引用），
知识增量 = 大规模 blend 的批量交叉校验模式与四集合差异的如实记录口径。

## R47 语言预检记录
`lang-preflight debian-science 1.15 --src <src>` → `detected_language=c`、exit 0
（`expected=cpp`，c↔cpp 兼容族）。原因为检测器按"构建系统优先"路径将
"顶层 Makefile 仅 include blends-dev + 零可统计源文件"归入 c/cpp 族。
本包实际为纯打包元数据，按 metadata/registry 包路线适配（非 C/C++ 编译，也不硬做空壳）。
