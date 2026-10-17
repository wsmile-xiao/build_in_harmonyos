# DRAFT-ohos-distro-subproject-standalone-packaging — 发行版内子组件可独立成包（版本取父发行版）

> Contributor: 5C7E / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-distro-subproject-standalone-packaging`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E277` | 图谱 | 库自带 vendored 依赖、registry 无配方时，在 `build()` 内**编译子项目到 staging** | 那是"**必须**连带编译子项目才能出产物"；**本条是"子组件可以单独出来"**，目的是**避免连带无关依赖**。方向相反 |
| `E425` | 图谱 | pico-sdk 的外部 submodule 可保持空目录，但需**限定当前包功能范围** | 那讲 submodule 空目录与范围限定；本条讲**同 tarball 内多组件的归属与版本命名** |
| `DRAFT-boost1.84-pkg-rename-archive` | 草稿 | **同源码双包名并行**（boost/1.84.0 与 boost1.84）的五处元数据同步 | 那条讲同一份源码**换个包名**并行归档；本条讲**同一 tarball 内不同组件**各成一包 |

**全库查证**：`AC_CONFIG_SUBDIRS`、`oath-toolkit`、`父发行版`、
`消费者声明.*非发行号` 等关键词**命中全 0**；
`liboath` / `oathtool` 亦命中 0。`子项目` 有 10 处命中，但经逐条核对（E277 / E355 /
E425 / E426 等），均非"发行版内子组件独立成包"这一机制。

## Scope（何时用）

上游把**多个库**放在同一 tarball、用 `AC_CONFIG_SUBDIRS` 组织的发行版
（oath-toolkit、gnupg 家族、util-linux 等）。

实测样本：**oath-toolkit 2.6.14** —— 含 5 个组件：

```
liboath  libpskc  pam_oath  oathtool  pskctool
```

## Symptom

若不判断就默认"必须整体构建"，会平白引入无关组件的依赖：

| 组件 | 整体构建会引入的额外依赖 |
|---|---|
| `pam_oath` | **linux-pam** |
| `oathtool` | 整个 OATH 栈 |

简单库因此变成依赖地狱；且一个包覆盖多库不利于按需消费与单独升级。

## Root Cause

发行版 tarball 内的子组件**往往可以独立成包**。实测 libpskc 三条判据全部成立：

| 判据 | 实测 |
|---|---|
| **① 自带预生成构建文件** | `libpskc/configure`（Autoconf 2.72）+ `Makefile.in` + `aclocal.m4` **齐备** → 可就地 `./configure && make`，**无需 autoreconf、无需先建父目录** |
| **② 不依赖兄弟库** | `libpskc/Makefile.am` 仅 `LIBADD = gl/libgnu.la`；源码中**无** `#include <liboath/...>` |
| **③ 版本取父发行版** | `AC_INIT([libpskc], [2.6.14])` = oath-toolkit 的版本（组件不单独发版）|

### ⚠️ 版本号陷阱（本条的另一个要点）

消费者（如 openconnect）在 pkg-config 里声明的是：

```
libpskc >= 2.2.0
```

这是**消费者自身的最低要求表达式**，**不是上游发行号**。若据此给 conan 包命名
（`libpskc/2.2.0`），会造出一个**不对应任何真实上游发行**的版本：

- 无法与 tarball 的 sha256 对应（溯源自证断裂）；
- 无法与制品仓其余版本排序对齐（R40 / L0n 的版本目录规则随之失效）。

**正确做法**：版本取**父发行版号** `2.6.14`，并在 `notes.md` / `manifest.yaml`
写明该版本来源是父发行版。

## Recommended Solution

### 主方案（priority 1）— 独立成包 + 父发行版版本号

1. `source()` 取父发行版 tarball（`strip_root=True`）；
2. `build()` / `package()` 的 cwd 指向 `<source_folder>/<comp>/`，直接跑组件自带的
   `./configure`（无需 autoreconf、无需父目录），按需加 `--disable-gtk-doc` 等裁掉文档；
3. **版本号取父发行版号**，并在 notes 写明来源；
4. 在 `notes.md` 记录"组件不依赖兄弟库"的实测依据，并说明同发行版其余组件（若有
   消费者）应**另行成包**（对应 JC6 单 PR 单软件）。

> 若组件**确有**独立于父发行版的版本（`AC_INIT` 与父版本不同），则以组件自身版本
> 为准，并在 notes 说明差异 —— **先验后断**。

### 回退方案（priority 2）— 整体一个包

若组件**确实**依赖兄弟库，或其 `configure` **未预生成**而必须先由父目录生成
（需 autoreconf 或父 Makefile 驱动），则退化为整体一个包：
`cpp_info.libs` 列全部库、`include` 列各组件头目录。
代价：引入无关组件的依赖与构建时间。

### 禁止做法

- ❌ 用**消费者声明的最低版本**作为 conan 版本 —— 会造出凭空版本，溯源断裂；
- ❌ 不核验就假定"必须先建父目录 / 必须先 autoreconf" —— 发行版 tarball 通常已预生成
  `configure`，白做工作量甚至误改上游冻结的构建脚本。

## 实测证据（2026-09-16，libpskc 2.6.14 适配）

| 项 | 结果 |
|---|---|
| 上游组织方式 | 顶层 `AC_CONFIG_SUBDIRS([liboath])` + 条件追加 `libpskc` / `pam_oath` |
| libpskc 自带构建文件 | `configure`（Autoconf 2.72）、`Makefile.in`、`aclocal.m4` 齐备 |
| 兄弟库依赖 | **无**（`LIBADD = gl/libgnu.la`；无 `include <liboath/...>`）|
| 版本 | `AC_INIT([libpskc], [2.6.14])` = 父发行版号 |
| 交付形态 | 独立 conan 包 `libpskc/2.6.14`，只构建 `gl schemas include .` 子目录 |
| 硬依赖 | 仅 libxml2（`AC_MSG_ERROR` 强制）——避免了整体构建会引入的 linux-pam |
| 构建结果 | `conan create` exit=0，上游 `make check` + 消费者测试通过 |

## 测试覆盖边界

本条处理"**发行版内子组件独立成包**"。区分相邻情形：

- **必须**连带编译子项目才能出产物 → `E277`；
- **同源码换包名**并行归档 → `DRAFT-boost1.84-pkg-rename-archive`；
- submodule 空目录与功能范围限定 → `E425`；
- 可选依赖缺失时的降级语义 → `DRAFT-ohos-optional-dep-silent-degrade-stub-api`。

## 关联条目

- 相似：`E277`（vendored 子项目必须编译）、`E425`（submodule 与范围限定）
- 差异：见上方差异化定位表
