# DRAFT-debian-pure-blends-metapackage-to-conan-metadata-registry

> Debian Pure Blends / metapackage 映射到 Conan metadata/registry package 的通用方法
> 实例：`debichem` 0.0.12（PR #9205 ｜ `acd9965a1a`）、
> `debian-parl` 1.9.33+nmu1（PR #9217 ｜ `4617d4b714`）——均 HarmonyOS PASS / CI PASS

## 问题 (Problem / Trigger)

有一类 Debian 项目**不是编译库**：没有 ELF/library、没有真实 build 步骤，
一个 source package 生成多个 `Architecture: all` 包，其真实价值是
**task 定义 / 依赖声明 / 发行画像 metadata / 安装器配方**。

- `debichem` 0.0.12：Debian Pure Blend（计算化学），1 source → `debichem-tasks`
  （tasksel 描述）+ 12 个 `debichem-<task>` metapackage；12 个 metapackage 本体只有
  一行标题小文件 + doc。
- `debian-parl` 1.9.33+nmu1：DebianParl（boxer 配方），1 source → `parl-data`
  （D-I preseed 数据）+ `parl-desktop` / `-world` / `-eu` / `-strict` 四个纯声明元包
  （world/eu/strict 除 doc 外零文件）。

## 根因 (Root Cause)

Debian metapackage 的「功能」存在于 **依赖图（Depends/Recommends/Suggests/Conflicts）+
task/desc 定义 + metadata + 安装器配方**；而 Conan package model 偏向
library / executable / headers / 具体运行资产，且**无语义**承载
`Recommends`/`Suggests`/`Conflicts`/`arch:all`，也无「一个 recipe 出多个包」。
二者 package model 不同：把 Debian `Depends` 机械映射为 Conan `requires` 会产生
**虚假、不可满足或错配**的依赖图（Debian 包名 ≠ 同源 Conan 包，且多为
firefox-esr/libreoffice/task-*/locale 数据等 OS/桌面级包）。

## 通用方案 (Portable Solution)

**单个 Conan data/metadata(registry) 包**保存源项目的有效语义：

1. **装真实上游产物**
   - debichem：12 个 Deb822 task 文件原文 + genblends 生成的 tasksel `debichem-tasks.desc`
     + build 期纯解析派生的 `registry.json`（记录 Debian 旧格式语义：无 `Format:` 头的
     task 文件其 `Depends:` 在 metapackage 中降级为 `Recommends:`）。
   - debian-parl：boxer `nodes/*.yml`（class 引用）+ `skel/*.in` + Makefile/NEWS/TODO
     + 派生 `debian-metadata.json`（5 元包 Depends/Suggests/Conflicts 计数、profile
     include/avoid、boxer-data 约束；出处=官方 .deb）。
2. **默认零 `requires`**，依赖按分类写入 metadata：
   | Debian 关系 | 判定 | Conan 动作 |
   |---|---|---|
   | Build-Depends | 构建期，与消费者无关 | 不 requires；记 metadata |
   | Depends → 可链接库且仓库同源同版已发布 | 真实运行依赖 | 记 metadata；**本例无此情形** |
   | Depends → OS/发行版软件或 locale 数据 | OS dependency | 不 requires；记 metadata |
   | Recommends / Suggests | 软关系 | 永不 requires；记 metadata |
   | Conflicts（strict 的 avoid） | Conan 无此概念 | 记 metadata；不做包操作 |
3. **保存元包间关系**（`debichem-tasks (=version)`、变体=基础+增量、strict Conflicts）于 JSON。
4. **test_package 验证 registry/tasks/desc/关系一致性**，不运行被引用程序。
5. **诚实边界**：不声称 Conan 包能安装完整 Debian desktop/blend；不把 changelog 声称但未入
   实发 .deb 的项当产物；不制造空 `.so` / 假 executable。

### Multi-package mapping（不一定 1:1 拆包）

`1 source package → N binary/meta package` 在 Conan 侧**不必**拆成 N 个 package
（Conan 无 multi-package recipe，且 `debichem-tasks (=version)` 之类关系在 Conan 无意义）。
若目标是保存源项目有效语义，建模为 **single Conan metadata/registry package**，
在其内部 `registry.json` 表达多个 Debian binary/meta package 即可。

## 验证 (Verification，真实证据)

- **debichem**：conan create PASS；test_package：tasks=12、tasksel desc Task 数=13
  （1 父 + 12 子）、desc `Key` 集合 == tasks 目录、`registry.json` 与打包任务文件的
  `Task:/Depends:/Suggests:` 交叉复核一致、包名符合 Debian 命名规范；与官方 0.0.12 .deb
  结构核对。HarmonyOS 真机 PASS，CI PASS（`acd9965a1a`）。
- **debian-parl**：conan create PASS；test_package：3 个 boxer node（class 引用
  `Task.harden.desktop` / `Desktop.locale.EU` / `Desktop.locale`）+ 2 个 skel 模板 +
  Makefile/NEWS/TODO 存在；metadata 中 5 元包真实依赖计数一致。HarmonyOS 真机 PASS，
  CI PASS（`4617d4b714`）。
- **诚实边界（保留）**：debichem 0.0.12 changelog 声称新增的
  comet-ms/mopac/xtb/openmolcas/libdbcsr-dev/libbtas-dev 未出现在 0.0.12 实发 .deb
  （genblends 的 apt 可用性过滤），已在 notes 披露；`visualisation` 标题 "3D Visualization"
  与包名拼写不一致（上游事实）。debian-parl 的 Conan 包**不含** boxer 生成的 preseed 成品
  （真实数据在 parl-data .deb），不宣称可安装 DebianParl 桌面。

证据文件：`ohos-farm/runtime/research/debichem.md`、`debian-parl.md`、
`ohos-farm/logs/harmony-verify/{debichem-0.0.12,debian-parl-1.9.33-nmu1}-WIN01-*.log`、
PR #9205 / #9217、recipe `archives/d/debichem/0.0.12/` 与 `archives/d/debian-parl/1.9.33+nmu1/`。

## 适用范围 (Applicable)

- Debian Pure Blends、metapackage 集合、task packages、dependency-only packages、
  installer/profile packages、发行版配置包（distro configuration bundles）；
- 任何「一 source 多 arch:all 包、真实价值在依赖/任务/metadata」的项目作为
  metadata/config/data 资产入库。

## 不适用 (Not Applicable)

- 元包实际包含关键 runtime binary（应直接适配该 binary）。
- 强依赖 Debian package manager 事务语义（安装/删除/配置触发）。
- 必须真正安装所有 downstream applications 才有意义的项目（本方法只保存声明，不复现安装结果）。

## 与既有条目查重 (Dedup)

- `blends` / `metapackage` / `meta package` / `pure blend` / `Suggests` / `task package`：
  knowledge/ **0 命中**；`Recommends` 仅 1 处无关命中（cmake 草稿正文）。
- 邻居（非等价）：E241（data/规则清单型库完整性）、E243（协议数据包 generator 测试）、
  E255（资源数据包）、E536（固件资源包）——均为「数据打包/验证」，**非** Debian
  metapackage 语义映射；`knowledge/drafts` 的 boost `meta-package-requires-aggregate`
  是 C++ header 聚合（无真实内容），与本条无关且属受限提示。
- 无等价条目 → **新立条目**（debichem + debian-parl 合并为一条通用方法，两个实例）。

## 潜在复用 (Potential Reuse，仓库真实命中)

- 本仓已入库的两个真实实例：`archives/d/debichem/0.0.12`、`archives/d/debian-parl/1.9.33+nmu1`。
- 同类「数据/资源包」真实先例（可复用打包与验证骨架）：`archives/c/ca-certificates`、
  `archives/s/spdx-licenses/3.28.0`、`archives/h/hunspell-en`、
  `archives/l/linux-firmware-brcm/20260622`（对应 E241/E255/E536）。
- 尚未入库、**未来可套用本方法**的 Debian Pure Blends（如 debian-science/debian-med/
  debian-edu 等）——本仓目前**无**其他 blend 归档（如实说明，不作为已存在候选）。
