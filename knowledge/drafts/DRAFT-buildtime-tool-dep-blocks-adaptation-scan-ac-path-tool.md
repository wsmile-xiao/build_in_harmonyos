# DRAFT-buildtime-tool-dep-blocks-adaptation-scan-ac-path-tool — 适配上游库前的隐形阻塞：其「构建期外部程序」硬依赖

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: dependency / build / autotools / cmake

## 相关既有条目（同族差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **`DRAFT-postgresql-18.3-config-sub-ohos-native-build`** | 已覆盖「`config.sub` 自带 `linux-ohos` 识别 → 显式 `--build` 即可，无需外置文件」。**本条不重复该结论**（gperf 实测确认同一现象，仅作为"动手前先实测"的例证一句带过）|
| `DRAFT-prebuilt-bindir-tool-relocated-runpath` | 讲**构建期工具的 RUNPATH/加载**问题（工具存在但加载失败）；本条讲**工具根本不在仓库**（未适配）时的依赖链阻塞与**开工前扫描方法**——角度不同 |
| **E305** | 讲"test_package 不应硬依赖外部工具"；本条讲的是**构建期**（configure/make）的工具，时点与结论均不同 |
| **`DRAFT-ohos-configure-ac-cv-path-tool-override`** | 同样围绕 `AC_PATH_TOOL` 展开，但**失败模式不同**：那条讲「探测**找到了**工具、但找错了」（命中系统 `curl-config` 而非私有 prefix）→ 解法是**用 configure cache 变量覆盖**；本条讲「工具**根本不存在**（既无包也未适配）」→ `AC_PATH_TOOL` 配合 `AC_MSG_ERROR` **直接硬失败**，cache 覆盖无用，只能**先把工具适配出来**。二者互补 |

> 查重（2026-09-12）：`构建期依赖.*工具` / `依赖链.*工具` / `必须先适配.*工具` 命中 **各 0** —— 确认为空白领域；另就 `AC_PATH_TOOL` 与 `DRAFT-ohos-configure-ac-cv-path-tool-override` 做了失败模式对照（见上表末行）。

## Scope（何时用）

从源码构建某个库（尤其依赖链深处的库）时，**开工前**用于排查"会不会被一个没适配的工具卡住"。

## 根因：依赖链有**两层**，通常只查了第一层

| 层 | 形态 | 缺失时的表现 |
|----|------|-------------|
| ① **链接期依赖**（库/头）| 显式写在 conanfile / bundler 里 | 依赖解析阶段**立刻**暴露 |
| ② **构建期外部程序**（代码生成器/解析器生成器/文档器）| configure/make 运行时以 `AC_PATH_TOOL` / `find_program` 出现 | **构建中途**才炸，且常是**硬失败** |

第②层最容易成为**隐形阻塞**：它不在依赖清单里、不产出为"包"，而且**可能无法从 tarball 绕过**。

### 实测：eudev 3.2.14 ← gperf（作为 apt 的前置）

```
configure.ac:   AC_PATH_TOOL(GPERF, gperf)   →  缺失即 AC_MSG_ERROR（硬失败，非可选）
```

其输入 `keyboard-keys-from-name.gperf` **不在官方 tarball 中**，而是由 Makefile 规则在**构建期**：

```
keyboard-keys.txt  --AWK-->  keyboard-keys-from-name.gperf  --gperf-->  keyboard-keys-from-name.h
                                                                         （列入 BUILT_SOURCES）
```

实测官方 tarball 内**既无 `.gperf` 也无 `.h`**（全树搜索 **0 命中**）→ **无法通过"预先放好产物"绕过**。

而 **ohpcd 没有 gperf 包**（main 上仅有 3.1 的 manifest/notes，**无 conanfile**）→ 想适配 eudev（进而 apt），**必须先把 gperf 适配掉**。

### 同源实例（本条通用性的佐证）

**triehash 之于 apt**：apt 的 `CMakeLists.txt` 对 triehash 是 `find_program` + **`FATAL_ERROR`**，同样**无法用 CMake 选项关闭**。

### ⚠️ 关键判据

这类依赖**不会**在"依赖分析"阶段报错，而是在**构建中途**炸。若等到 CI 才发现，会白跑一轮构建。

## 方案：先扫描 → 判可绕性 → 核对仓库 → 先适配工具

### ① 扫描：列出目标库构建期的全部外部程序

```bash
# autotools
grep -nE 'AC_PATH_(TOOL|PROG)|AC_CHECK_PROG' <src>/configure.ac

# CMake —— 重点是 REQUIRED 与随后紧跟的不带条件的 FATAL_ERROR
grep -rnE 'find_program\(|FATAL_ERROR' <src>/CMakeLists.txt
```

### ② 判定可绕性（关键）

```bash
tar tf <src>.tar.* | grep -iE '<工具输入|工具产物>'
```

- 输入与产物**都在** tarball → 可预置绕过
- **都不在** → 构建期生成，**无法绕过**，只能真的把工具做出来

### ③ 核对仓库 —— 注意"笔记 ≠ 已适配"

```bash
conan search '<tool>/*' -r=ohpcd
```

⚠️ 仓库里可能存在**只有 `manifest`/`notes`/`README`、没有 `conanfile`** 的占位目录（实测 **gperf 3.1**、**triehash 0.3** 均如此）——它们**不是可用包**。

### ④ 先适配前置工具

工具通常比目标库**小得多**：

- **gperf**：纯 C + autotools
- **triehash**：纯 Perl 脚本

→ 先出工具包并发布 ohpcd，再适配目标库。

### ⑤ 如实记录依赖关系

在目标库的 PR/manifest 中写明：它依赖哪个工具包、以及**为何构建期就必需** —— 避免后续维护者误以为是可选。

## 备选（fallback）

若该工具对应的功能能**完全关闭**（configure 提供 `--disable-<feature>` **且不是** `FATAL_ERROR`），可先关掉该功能完成主体适配。

**前提是必须确认它是真可选** —— 实测 apt 对 triehash 是 `FATAL_ERROR`（不可关），eudev 对 gperf 同样是硬失败，**这类就不能走本备选**。若走了本备选，须在 manifest/PR 中**如实声明哪些功能被关闭**，不可暗示功能完整。

## 禁止

- ❌ **"没找到工具就跳过"** —— 构建期工具是**硬失败**（`AC_MSG_ERROR` / `FATAL_ERROR`），缺了连构建都无法开始，跳过等于放弃适配，且会浪费一轮 CI
- ❌ **"main 上有 manifest/notes 就视为已适配"** —— 存在只有元数据、没有 `conanfile` 的占位目录（gperf 3.1、triehash 0.3 实测均如此），**不是可用包**
- ❌ **"手工预置生成物绕过工具"** —— 这类输入/产物通常是**构建期由脚本生成**的（不在 tarball 内），手工预置来源不明、易与源码版本漂移不一致，且 CI 不可复现

## 实证

- **gperf/3.3（PR #9620）** —— 为解开 **eudev 3.2.14（PR #9614）**的构建阻塞而适配：
  - `configure.ac` 的 `AC_PATH_TOOL(GPERF, gperf)` 缺失即 `AC_MSG_ERROR`
  - `keyboard-keys-from-name.gperf` 由 Makefile 规则**构建期**用 AWK 生成 → 官方 tarball 既无 `.gperf` 也无 `.h`（全树搜索 **0 命中**）→ **无法从 tarball 绕过**
  - ohpcd 无 gperf 包（main 仅 3.1 笔记、**无 conanfile**）
- **同源实例**：apt 对 triehash 为 `find_program` + **`FATAL_ERROR`**（无法用选项关闭）
- **附**：gperf 3.3 实测 `config.sub` **已原生支持** `linux-ohos*` —— 该现象已由 `DRAFT-postgresql-18.3-config-sub-ohos-native-build` 覆盖，本条不重复，仅作为"动手前先实测"的例证
