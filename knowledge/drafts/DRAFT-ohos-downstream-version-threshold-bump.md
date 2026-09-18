# DRAFT-ohos-downstream-version-threshold-bump — 下游库的版本门槛驱动一串基础库升级

> Contributor: 7E31 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-downstream-version-threshold-bump`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-dep-version-assert-warn`（同批）| 草稿 | 上游库对依赖做**版本区间硬断言**（`assert` 被 try/except 包住 → import 时只发 `RequestsDependencyWarning`）| 那条是**运行期、仅告警、可继续用**；本条是**配置期、硬中断、无法绕过的源码内门槛**。判据不同：那条要实测"告警是否 gate 行为"，本条要量"门槛拓扑 + 每个升级的构建契约" |
| `E6341` | 图谱 | 同上（requests 版本区间）| 同上，属包管理器层面的区间声明 |
| `E348` / `E481` | 图谱 | `Run-time dependency xxx found: NO` / `Dependency .* not found` | 那是**依赖根本缺失**（无任何版本提供）；本条是**依赖存在但版本不足**，报错形如 `found: NO. Found 1.22.0.1 but need: '>=1.24.0'`，处置方式完全不同（缺失→新适配；版本不足→升级既有包）|

**全库查证**：对 `版本门槛` / `but need:` / `downstream.*require.*bump` /
`>=1.24.0` / `>=1.8.0` 等关键词，在 `knowledge/index.tsv`、`knowledge/graph/index.tsv`、
`knowledge/graph/*.kv`、`knowledge/doc/*.md`、`knowledge/drafts/*.kv`、
`knowledge/drafts/*.md` 中 grep —— 仅 `DRAFT-gnupg-family-min-libgpg-error-version-varies-per-library`
命中（讲"同一依赖在不同 GnuPG 组件里最低版本要求不同、变量名有两套"），
**与本条的"下游门槛驱动串式升级 + 逐个判构建契约"命中 0 条**。

## Scope（何时用）

被适配的下游库在**构建系统**里对基础依赖声明硬性最低版本。

实测实例（wlroots 0.20.1）：

```
wlroots-0.20.1/meson.build:
    dependency('wayland-server',     version: '>=1.24.0')
    dependency('xkbcommon',          version: '>=1.8.0')
    dependency('wayland-protocols',  version: '>=1.47')
```

而制品仓当时为 `wayland 1.22.0.1` / `libxkbcommon 1.6.0` / `wayland-protocols 1.36.1`
—— **三个门槛同时不满足**。

## Symptom

用制品仓现有版本的真实 `.pc` 跑下游配置：

```
$ meson setup build wlroots-0.20.1
Dependency wayland-server found: NO. Found 1.22.0.1 but need: '>=1.24.0'
ERROR: Automatic wrap-based subproject downloading is disabled
```

两个特征要抓住：

1. 报错**同时给出"当前版本"与"所需版本"** —— 这是与"依赖缺失"（`found: NO` 无版本）
   的区分点；
2. 伴随 `Automatic wrap-based subproject downloading is disabled` —— meson 本可自动
   下载依赖顶替，但被禁用（也不该启用），故这是**硬停**。

## Root Cause

门槛要求的**不是代码改动，而是基础库版本本身**。因此：

- ❌ 打补丁改下游源码去绕过 `version` 检查是错的 —— 等于宣称"低版本也兼容上游未验证的
  组合"，风险被推到运行期（未定义符号 / ABI 不匹配 / 接口缺失）；
- ✅ 唯一正解是把基础库升到门槛之上。

**关键在于这类门槛往往成串出现，而每个升级的难度不同**，必须逐个核对构建契约：

| 基础库 | 升级结果 | 构建契约变化 | 实测量级 |
|---|---|---|---|
| `wayland` 1.22.0.1 → **1.24.0** | 依赖、meson 选项**完全一致** | 无（配方整体沿用）| 改动最小 |
| `libxkbcommon` 1.6.0 → **1.8.0** | **新增两个默认 true 的选项**（`enable-wayland`、`enable-bash-completion`）| **有**：`enable-wayland` 缺依赖时是 `error()` 级，照搬旧配方**配置期直接失败** | 中等 |
| `wayland-protocols` 1.36.1 → **1.47** | 抬高了对**内嵌工具**的要求（`tests=true` 时 `wayland-scanner >= 1.23.0`）；协议 XML 44→57 | **有**：内嵌 scanner 的源码版本与 `.pc` 版本号都要跟着改 | 最大 |

即「版本号 +0.1」不能统一估工 —— 同样的"小版本升级"背后是三种完全不同量的工作。

## Recommended Solution

### 主方案（priority 1）— `dependency-first`（先量拓扑，再逐个升）

**步骤 1：枚举门槛，列出对照表**

```bash
# 下游源码里所有带版本的依赖声明
grep -rnE "dependency\([^)]*version" <downstream>/meson.build
# cmake 场景：find_package(<pkg> <ver> REQUIRED)
```

产出「依赖 → 门槛版本 → 制品仓现有版本 → 是否达标」表。

**步骤 2：逐个判定"构建契约是否变化"**（决定沿用还是重写配方）

对照检查项：依赖项集合、构建选项**名称与默认值**、内嵌工具要求、产物清单。
实测里三种情形各占一个，说明这一步不能省。

**步骤 3：按拓扑序升级，各自独立 PR**（W2 / PF4）

基础件之间可能有先后依赖（若 A 的新版本构建需要 B 的新版本，则 B 先）。每个升级都要
真实跑 `conan create` + 上游测试回填通过率。

**步骤 4：评估影响面**

基础件被别的包依赖，升级后要确认既有下游仍可编译（`grep` 谁 `requires` 了它）。

### 回退方案（priority 2）— `disable-the-feature-gate`

部分门槛是**条件性**的。实测实例：

```meson
# wayland-protocols-1.47/meson.build:11
dep_scanner = dependency('wayland-scanner',
    version: get_option('tests') ? '>=1.23.0' : '>=1.20.0',
    native: true, ...)
```

即 `tests=false` 时门槛从 1.23.0 降到 1.20.0。若该特性非必需，关掉可把门槛降回可满足范围。

> ⚠️ 但这是**降低验证强度**的处置，必须在 `notes.md` 显式申报关掉的覆盖面与代价，
> 不得静默关闭（R51 精神）。

### 禁止做法

- ❌ 把门槛当普通编译错误，打补丁改下游源码绕过版本检查。
- ❌ 把多个基础库升级塞进同一个 PR（无法单独回滚/验证，违反 W2 与 PF4）。

## 实测证据（2026-09-16）

| 步骤 | 结果 |
|---|---|
| 门槛枚举 | wlroots 0.20.1 的 3 个必需依赖门槛全部不达标（wayland/xkbcommon/wayland-protocols）|
| 配置期硬失败复现 | 用 1.22.0.1 的真实 `.pc` → `found: NO. Found 1.22.0.1 but need: '>=1.24.0'` |
| 三个升级的实际差异 | wayland 契约无变化（整体沿用）；libxkbcommon 新增 2 个默认 true 选项（`enable-wayland` 为 error 级）；wayland-protocols 内嵌 scanner 需从 1.22.0 换到 1.24.0 |
| 升级后 | 三库各自 `conan create` 通过，上游测试分别 18/26、19/20、179/179 |

## 测试覆盖边界

本条只处理"构建系统层面的**版本不足**"。区分两种相邻情形：

- 依赖**缺失**（无任何提供方）→ 走新适配（参见 `E481` 类条目的思路）；
- 依赖存在但版本不足 → 本条（升级既有包）。

另外，"是否需要开 `tests`"会反过来影响门槛高度，做决定时要一并考虑——
本批选择开 tests 并升级 scanner，而非关 tests 降门槛。

## 关联条目

- 相似：`DRAFT-ohos-dep-version-assert-warn`（版本区间断言，仅告警）、
  `E6341`（同上）、`E348` / `E481`（依赖缺失，非版本不足）
- 差异：见上方差异化定位表
