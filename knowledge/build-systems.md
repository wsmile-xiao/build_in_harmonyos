# 构建系统识别与适配策略

## 1. 构建系统类型

| 构建系统 | 识别特征 | 配置文件 | 适配方式 | 示例软件 |
|---------|---------|---------|---------|---------|
| **Autotools** | 存在 `configure` 脚本 | `configure.ac`, `Makefile.am` | 修改 `config.guess`, `config.sub` | libffi, bash, coreutils |
| **CMake** | 存在 `CMakeLists.txt` | `CMakeLists.txt`, `*.cmake` | 添加平台检测 | zlib |
| **自定义 Perl** | 存在 `Configure` (大写) | `Configurations/*.conf` | 添加配置文件 | OpenSSL |
| **Meson** | 存在 `meson.build` | `meson.build` | 添加平台检测 | systemd |
| **Makefile** | 存在 `Makefile` | `Makefile`, `*.mk` | 直接修改 | bzip2 |
| **QMake** | 存在 `.pro` 文件 | `*.pro` | 修改 .pro 文件 | Qt 项目 |

## 2. 构建系统识别命令

```bash
# 检测脚本
check_build_system() {
    if [ -f "configure" ] && [ -x "configure" ]; then
        echo "Autotools"
    elif [ -f "CMakeLists.txt" ]; then
        echo "CMake"
    elif [ -f "Configure" ] && [ -x "Configure" ]; then
        echo "Custom-Perl"
    elif [ -f "meson.build" ]; then
        echo "Meson"
    elif [ -f "Makefile" ] || ls *.mk 1>/dev/null 2>&1; then
        echo "Makefile"
    else
        echo "Unknown"
    fi
}
```

## 3. Autotools 适配

### 3.0 核心原则：不欺骗构建系统

> **重要原则**：永远不要通过伪造三元组（如 `--build=aarch64-unknown-linux-gnu`）来欺骗 configure。
> 
> 这种做法虽然可能暂时解决问题，但会导致：
> 1. 构建系统对平台特性的错误判断
> 2. 缺失正确的平台特定代码路径
> 3. 编译产物可能与预期不符
> 4. 无法复用补丁和经验

**正确做法**：为 HarmonyOS 添加正式的三元组支持：
1. 修改 `config.guess` 添加 HarmonyOS 识别
2. 修改 `config.sub` 添加 `linux-ohos` 支持
3. 如有必要，修改 `configure.ac` 添加平台分支

**三元组格式**：`{架构}-{厂商}-{操作系统}`
- 标准格式：`aarch64-unknown-linux-ohos`
- 表示：ARM64 架构，未知厂商，基于 Linux 的 HarmonyOS

### 3.1 修改 config.guess

> **⚠️ 关键发现（F002）**：config.guess 有**多个** `case ... in` 语句，HarmonyOS 检测代码必须插入**主 case**（匹配 `$UNAME_MACHINE:$UNAME_SYSTEM:...`），而非其他位置。插错位置会导致检测完全失效。

#### config.guess 结构图示

```
config.guess 执行流程（GNU 2025-07-10 版，~1818 行）
│
├── [行 1-50]   头部/版权/shebang
├── [行 51-100]  辅助函数定义
│
├── [行 ~120]    ┌─────────────────────────────────────┐
│   ⭐ 主 CASE    │ case $UNAME_MACHINE:$UNAME_SYSTEM:  │ ← 必须在此插入！
│   （行 ~158）   │     $UNAME_RELEASE:$UNAME_VERSION   │
│                 │   in                                │
│                 │     *:HarmonyOS:*:*)                │ ← OHOS 插入点
│                 │         GUESS=...-linux-ohos        │
│                 │         ;;                          │
│                 │     *:Darwin:*)                     │
│                 │     *:QNX:*)                        │
│                 │     ...                             │
│                 └─────────────────────────────────────┘
│
├── [行 ~200]    LIBC 检测（#ifdef __OHOS__ → LIBC=ohos）
│
├── [行 ~239]    ┌─────────────────────────────────────┐
│   ❌ 错误位置！ │ case "$UNAME_RELEASE" in             │ ← 不要在这里插入
│   ($UNAME_REL)  │   *:HarmonyOS:*)                    │   （只匹配 RELEASE 部分）
│                 └─────────────────────────────────────┘
│
├── [行 ~300+]   各架构/系统的精细匹配
└── [末尾]       输出 GUESS 变量
```

#### 插入规则

| 规则 | 说明 |
|------|------|
| **必须插入主 case** | 匹配完整的四元组 `$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION` |
| **模式用 `*:HarmonyOS:*:*`** | 通配架构和版本，精确匹配系统名 |
| **在 Darwin/QNX 之前** | 字母序 H 在 D/Q 之间 |
| **不要插入 $UNAME_RELEASE case** | 那里只匹配版本号，不包含系统信息 |

#### 常见错误

| 错误做法 | 症状 | 正确做法 |
|---------|------|---------|
| 插入 `$UNAME_RELEASE` case | configure 仍报 "unrecognized system" | 插入主 case |
| 用 `*ohos*` 而非 `*:HarmonyOS:*:*` | 可能误匹配其他含 ohos 的字符串 | 用完整模式 |
| 只改一处不验证 | 静默失败，configure 用默认值 | 改完后 `./config.guess` 测试输出 |

#### 验证方法

```bash
# 修改后立即测试
cd /path/to/source
chmod +x config.guess
./config.guess
# 期望输出: aarch64-unknown-linux-ohos（或对应架构）

# 如果输出不是 *-ohos，说明插入位置错误
```

#### 两种修改策略

**策略 A：增量补丁（推荐用于旧版 config.guess）**

在两个位置添加代码：

**位置 1：LIBC 检测**
```bash
#if defined(__ANDROID__)
LIBC=android
#elif defined(__OHOS__)
LIBC=ohos
#else
```

**位置 2：主 case 系统识别（⭐ 关键位置）**
```bash
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        GUESS=$UNAME_MACHINE-unknown-linux-ohos
        ;;
    # ... 其他系统（Darwin, QNX 等）
```

**策略 B：整文件替换（推荐用于极旧版 config.guess < 2018）**

当原始 config.guess 太旧（如 2015 年 pkg-config 自带的），增量修补工作量大于替换：
- 从 GNU config.git 获取最新版（2025-07-10 或更新）
- 新版已内置 HarmonyOS 检测（`__OHOS__` + `*:HarmonyOS:*:*`）
- 补丁为整文件 diff（较大但可靠）

| 策略 | 适用场景 | 补丁大小 | 可上游性 |
|------|---------|---------|---------|
| A 增量 | config.guess 版本 ≥ 2018 | 小 (~20 行) | ✅ 高 |
| B 替换 | config.guess 版本 < 2018 | 大 (>3000 行) | ⚠️ 取决于 GNU 是否接受 |

### 3.2 修改 config.sub

> **⚠️ 关键发现（F003）**：config.sub 的 `maybe_os` 变量提取的是 OS 名的**末尾两段**（非一段），导致 case 匹配时模式必须是 `linux-ohos` 而非 `ohos-linux`。

#### config.sub 三阶段处理流程

```
输入三元组: aarch64-unknown-linux-ohos
│
├── 阶段①: maybe_os 预提取
│   │
│   │  从三元组中提取可能的 OS 标识符
│   │  规则: 取最后一个 '-' 分隔段及其前一段的组合
│   │
│   │  aarch64-unknown-linux-ohos
│   │                           ^^^^ ^^^^
│   │                           last  prev → maybe_os="linux-ohos"
│   │
│   │  ⚠️ 注意: 不是取最后一段 ("ohos")!
│   │     是取最后两段 ("linux-ohos")
│   │
│   ▼
├── 阶段②: case $maybe_os 匹配
│   │
│   │  case $maybe_os in
│   │      linux-android)      basic_os=linux-android ;;
│   │      linux-musl)         basic_os=linux-musl ;;  
│   │      linux-ohos)         basic_os=linux-ohos ;;   ← ⭐ OHOS 在这里!
│   │      linux-uclibc)       basic_os=linux-uclibc ;;
│   │  esac
│   │
│   │  ⚠️ 常见错误: 写成 ohos-linux) → 永远不匹配!
│   │     因为 maybe_os="linux-ohos" 不是 "ohos-linux"
│   │
│   ▼
├── 阶段③: case $os 后处理 / kernel-os 验证
│   │
│   │  进一步处理 basic_os，最终确定:
│   │  - basic_machine = aarch64-unknown
│   │  - basic_os = linux-ohos
│   │
│   │  同时需要在以下位置添加 ohos* 允许:
│   │  1. OS 允许列表: | ohos* \          (行 ~2075)
│   │  2. kernel-os 验证: | linux-ohos*- )  (行 ~2219)
│   │
│   ▼
└── 输出: 验证通过的三元组
```

#### 必须修改的三处位置

| # | 位置 | 修改内容 | 漏掉会怎样 |
|---|------|---------|-----------|
| 1 | `case $maybe_os` | 添加 `linux-ohos)` 分支 | basic_os 无法识别 |
| 2 | OS 允许列表 | 添加 `\| ohos* \` | "invalid OS" 错误 |
| 3 | kernel-os 验证 | 添加 `\| linux-ohos*- )` | 内核-OS 组合不合法 |

#### 完整补丁模板

```bash
# 位置 1: case $maybe_os（通常在 android-linux 之后）
linux-android)
    basic_machine=$field1-unknown
    basic_os=linux-android
    ;;
+ohos-linux)
+    basic_machine=$field1-unknown
+    basic_os=linux-ohos
+    ;;

# 位置 2: OS 允许列表（搜索 "| android*" 附近）
-            | android* \
+            | android* \
+            | ohos* \

# 位置 3: kernel-os 验证（搜索 "linux-uclibc*" 附近）
-            | linux-relibc*- | linux-uclibc*- )
+            | linux-relibc*- | linux-uclibc*- | linux-ohos*- )
```

### 3.3 编译命令

```bash
# 本地构建（最简配置）
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

### 3.4 交叉编译必须设置 --host/--build/--target

#### 问题描述

在鸿蒙上编译时，如果 configure 脚本不能通过 `config.guess` 正确识别系统，
或软件需要在鸿蒙上运行但构建系统和目标系统不同，必须显式设置
`--host`、`--build`、`--target` 参数。

#### 根因分析

autotools 的 configure 脚本使用三个概念来描述编译环境：

| 参数 | 含义 | 鸿蒙上的典型值 |
|------|------|---------------|
| `--build` | **构建系统**（正在编译的机器） | `aarch64-unknown-linux-ohos` |
| `--host` | **宿主系统**（编译产物运行的机器） | `aarch64-unknown-linux-ohos` |
| `--target` | **目标系统**（编译产物生成的代码运行的机器） | 通常与 `--host` 相同 |

如果 `config.guess` 返回了错误的三元组（或不支持的值），configure 会使用
错误的代码路径，导致：
- 选择了错误的系统调用封装
- 使用了不兼容的库路径
- 生成了错误的编译器标志

#### 解决方案

```bash
# 推荐方式：显式指定 build 和 host
./configure     --build=aarch64-unknown-linux-ohos     --host=aarch64-unknown-linux-ohos     --prefix=$HOME/usr/local

# 如果 config.guess 已正确修改（推荐优先修改 config.guess），
# 可以只指定 --host：
./configure --host=aarch64-unknown-linux-ohos --prefix=$HOME/usr/local
```

#### 影响范围

所有 config.guess/config.sub 未更新的 autotools 项目。

#### 相关知识

- [autotools-patterns.md §2-3](autotools-patterns.md#2-configguess-修改) — config.guess/config.sub 修改
- [harmonyos-specifics.md §15](harmonyos-specifics.md#15-configure-脚本不识别-ohos-平台变量) — configure 不识别 OHOS

> 来源：`archives/p/python/3.9.0/manifest.yaml`

### 3.5 交叉编译工具链的 include 路径需要显式指定

#### 问题描述

鸿蒙 SDK 的系统头文件和库文件不在标准路径（`/usr/include`、`/usr/lib`）下，
编译时如果未显式指定 include 路径，会导致找不到系统头文件或库文件。

#### 根因分析

鸿蒙 SDK 的工具链文件分布在 `/data/service/hnp/` 下：

| 资源类型 | 标准路径 | 鸿蒙 SDK 路径 |
|----------|----------|--------------|
| C 头文件 | `/usr/include` | `/data/service/hnp/sysroot/usr/include` |
| 系统库 | `/usr/lib` | `/data/service/hnp/sysroot/usr/lib` |
| LLVM 头文件 | `/usr/include/clang` | `/data/service/hnp/lib/clang/15.0.0/include` |

当 `configure` 或 Makefile 中的 `CPPFLAGS`/`CFLAGS` 未包含 SDK 的 include 路径时，
编译器找不到系统头文件。

#### 解决方案

```bash
# 方案 1：设置 CPPFLAGS 包含系统头文件路径
export CPPFLAGS="-I/data/service/hnp/sysroot/usr/include $CPPFLAGS"

# 方案 2：使用 --sysroot 指定系统根目录
export CFLAGS="--sysroot=/data/service/hnp/sysroot $CFLAGS"

# 方案 3：使用 clang 的内置路径（通常自动包含）
# clang --print-search-dirs | grep headers
# 检查 clang 是否自动包含 sysroot
clang -xc -E -v /dev/null 2>&1 | grep "^ "
```

#### 验证命令

```bash
# 确认编译器能找到系统头文件
echo '#include <stdio.h>' | clang -xc -E - | head -5

# 确认 SDK sysroot 存在
ls /data/service/hnp/sysroot/usr/include/stdio.h
```

#### 影响范围

所有需要系统头文件的 C/C++ 项目，尤其是那些 `CPPFLAGS` 未正确设置的项目。

#### 相关知识

- [error-patterns.md E015](error-patterns.md#e015-找不到头文件) — 找不到头文件的通用处理
- [harmonyos-specifics.md §17](harmonyos-specifics.md#17-系统-posix-头文件缺失) — POSIX 头文件缺失

> 来源：`archives/p/python/3.9.0/manifest.yaml`

### 3.6 Autotools 源码修改层级决策树

> **核心原则**：修改越靠近源头越好。生成文件（configure/Makefile）的修改是最后手段。

#### 层级优先级（从高到低）

```
优先级 ①（最佳）：configure.ac / CMakeLists.txt / 源码 .c/.h 文件
    ↓  autoconf/automake/cmake 重新生成
优先级 ②（可接受）：configure / Makefile.in（autoconf 生成的中间文件）
    ↓  config.status / make 重新生成
优先级 ③（ workaround）：Makefile（make 过程生成的文件）
    ↓ 直接生效，但 make clean 后丢失
优先级 ④（禁止）：sed 操作二进制/运行时修改已编译产物
```

#### 决策流程图

```
需要修改编译行为？
    │
    ├─ 软件有 configure.ac？
    │   └─ ✅ → ① 修改 configure.ac + re-autoconf
    │            例：添加 case "*ohos*)" 分支禁用某功能
    │
    ├─ 只有 configure（无 configure.ac）？
    │   └─ ✅ → ② 修改 configure 本身
    │            例：在平台检测 case 中添加 *ohos* 匹配
    │            ⚠️ 记录：此修改在 autoreconf 后会丢失
    │
    ├─ 需要改变编译标志/链接库？
    │   └─ 检查 Makefile.am 是否存在
    │       ├─ 有 → ① 修改 Makefile.am + re-automake
    │       └─ 无 → ② 修改 Makefile.in 或 ③ Makefile
    │
    └─ 需要修复源码 bug？
        └─ ✅ → ① 直接修改 .c/.h 文件（永远是最高优先级）
           必须带 #ifdef __OHOS__ 守卫
```

#### 各层级的典型场景和示例

| 层级 | 典型场景 | 示例 |
|------|---------|------|
| **①** 源码/配置源码 | 平台特定代码路径、功能开关 | `#ifdef __OHOS__` 守卫的替代实现 |
| **①** configure.ac | 新增平台检测、条件编译选项 | `case "*ohos*)" ohos=yes ;;` |
| **②** configure | 平台检测 case 分支、库搜索路径 | config.guess 已识别但 configure 未处理 |
| **②** Makefile.in | 链接标志、安装路径模板 | `LDFLAGS += -lxxx` for ohos |
| **③** Makefile | 临时调试、快速验证 | `CC = clang` 替换 |
| **④** ❌ 禁止 | sed 操作 configure/Makefile | 绝对不允许 |

#### 特殊情况：内嵌依赖的 config.guess

当软件内嵌了其他项目的旧版 config.guess（如 pkg-config 内嵌 glib 2.38.2 的 config.guess），**无法通过修改主包的 config.guess 解决**。

**策略选择**：

| 方案 | 可行性 | 推荐度 |
|------|--------|--------|
| A. 为内嵌依赖单独打补丁 | ✅ 最佳但工作量大 | ⭐⭐⭐ 长期目标 |
| B. 强制指定 --build/--host 覆盖 | ✅ 立即可行 | ⭐⭐ 短期 workaround |
| C. --with-internal-glib 禁用内嵌依赖 | 视软件而定 | ⭐ 如可用则最干净 |

**方案 B 的正确使用方式**：
```bash
# 使用 --build/--host 作为兜底，不是首选方案
# 必须在 manifest.yaml build_cleanliness 中记录为技术债务
./configure --prefix=$PREFIX \
    --build=aarch64-unknown-linux-ohos \
    --host=aarch64-unknown-linux-ohos
# 原因：glib 内嵌 config.guess(2014) 无 HarmonyOS 检测
# 改进计划：为 glib 的 config.guess 打补丁后去掉此参数
```

### 3.7 OHOS 平台隔离标准写法

> **原则**：所有平台特定的代码修改必须使用标准化的隔离写法，
> 确保 OHOS 相关代码易于识别、不影响其他平台、便于上游接受。

#### 三种标准模板

**模板 A：C/C++ 源码中的预编译守卫**

```c
/* HarmonyOS: <具体原因，如 "fstat() 对非文件 fd 返回 EACCES"> */
#ifdef __OHOS__
/* 替代实现或安全回退 */
static inline int ohos_fstat_compat(int fd, struct stat *st) {
    if (fstat(fd, st) == 0) return 0;
    if (errno == EACCES || errno == EPERM) {
        memset(st, 0, sizeof(*st));
        st->st_blksize = 4096;
        return 0;
    }
    return -1;
}
#define compat_fstat(fd, st) ohos_fstat_compat((fd), (st))
#else
#define compat_fstat(fd, st) fstat((fd), (st))
#endif
```

**模板 B：configure / configure.ac 中的平台分支**

```bash
# 在 configure.ac 中（优先级 ①）
case "$host_os" in
    *ohos*)
        # HarmonyOS 特定配置
        ac_cv_func_fstatat0=no      # 禁用不可靠的检测
        ;;
esac

# 在 configure 中（优先级 ②，如果无法修改 configure.ac）
# 找到对应的 case "$host_os" in 分支，添加 *ohos*) 模式
```

**模板 C：Makefile / Makefile.am 中的条件编译**

```makefile
# 在 Makefile.am 中（优先级 ①）
if OHOS
    CFLAGS += -D__OHOS__ -Wno-error=deprecated-declarations
endif

# 或在 configure.ac 中定义 AM_CONDITIONAL:
AM_CONDITIONAL([OHOS], [echo "$host_os" | grep -q "ohos"])
```

#### 命名规范

| 元素 | 规范 | 示例 |
|------|------|------|
| 宏/函数名前缀 | `ohos_` 或 `_ohos` | `ohos_fstat_compat()` |
| 变量名 | `_ohos` 后缀 | `ac_cv_func_xxx_ohos` |
| 补丁文件描述 | 以 `ohos-` 开头 | `0001-ohos-fix-fstat-for-non-file-fd.patch` |
| 条件编译注释 | 以 `HarmonyOS:` 开头 | `/* HarmonyOS: musl 不支持 */` |

### 3.8 补丁文件元数据规范（P0 三可原则的落地）

> 每个补丁文件必须包含完整的元数据 header，确保可追溯、可验证。

#### 必需的 header 字段

```diff
From: OpenHarmony PC Developer <community@example.com>
Date: Mon, 01 Jan 2026 00:00:00 +0000
Subject: [PATCH N/NN] ohos-fix-xxx-for-harmonyos

Description: 一句话说明修改原因（< 80 字符）
Origin: source | generated (二选一)
  - source: 基于原始源码与构建产物的 diff
  - generated: AI 生成的功能性修复（必须标注）
Upstream: yes | no | partial (三选一)
  - yes: 可直接提交给上游
  - no: OHOS 特有，不可上游
  - partial: 部分逻辑可上游，OHOS 条件编译部分除外
Source-Commit: <被修改文件的原始 commit hash，如已知>
  - 例: Source-Commit: a1b2c3d (config.guess 2025-07-10 from GNU)
  - 如未知则写 Source-Commit: unknown (需追溯)
Modification-Layer: ① | ② | ③ (对应 §3.6 决策树层级)
Knowledge-Ref: error-patterns.md E0XX / build-systems.md §X (关联知识条目)
---
```

#### 来源追溯要求

| 被修改的文件类型 | Source-Commit 要求 | 追溯方法 |
|-----------------|-------------------|---------|
| config.guess / config.sub | **必须** | GNU autoconf git repo 的 commit hash |
| configure（autoconf 生成） | 推荐 | 对应 configure.ac 版本的 autoconf 生成结果 |
| Makefile.in（automake 生成） | 推荐 | 对应 Makefile.am 版本的 automake 生成结果 |
| Makefile（make 生成） | 可选 | 通常不追溯（优先级③） |
| .c / .h 源码 | 必须 | 上游版本库的 commit hash |
| 内嵌依赖的文件 | **必须 + 单独标注** | 标注内嵌依赖的名称和版本 |

> **为什么需要 Source-Commit？**
> pkg-config 编译中发现：GNU 最新版 config.guess(2025-07-10) 居然不含 HarmonyOS 检测代码。
> 如果没有记录来源 commit hash，无法回溯"这个 config.guess 到底是从哪来的"、
> "是官方发行版还是某个发行版的 fork"。这直接影响补丁的可复现性。

### 3.9 Makefile sed 自动化机制

> 当必须在优先级③（Makefile）做修改时（如 glib 太老无法 re-autoconf），需要确保修改在 `make clean` 后不会丢失。

#### 问题场景

```
./configure → 生成 Makefile
sed -i 's/-Werror//' Makefile    # 临时修改
make && make install               # ✅ 成功
make clean                         # 清理
# 此时 Makefile 可能被重新生成或保留，取决于项目
./configure                        # 再次 configure
# sed 修改丢失！❌ 需要重新执行 sed
```

#### 推荐方案：post-configure hook 脚本

```bash
# 创建 scripts/post-configure-hook.sh（放在软件档案目录下）
#!/bin/sh
# post-configure-hook.sh — 在每次 ./configure 之后执行
# 用于处理无法通过补丁解决的优先级③修改

set -e

BUILD_DIR="${1:-.}"

# Example: glib Werror fix for pkg-config's embedded glib 2.38.2
if [ -f "$BUILD_DIR/glib/Makefile" ]; then
    sed -i 's/CFLAGS = /CFLAGS = -Wno-error=deprecated-declarations /' \
        "$BUILD_DIR/glib/Makefile"
    echo "  [hook] Applied glib CFLAGS workaround"
fi

echo "  [hook] post-configure complete"
```

**使用方式**：

```bash
# 在 Phase 3 编译执行中：
./configure --prefix=$PREFIX ...
bash scripts/post-configure-hook.sh "$(pwd)"   # ← 每次 configure 后执行
make -j1
```

**manifest.yaml 中记录**：

```yaml
build_config:
  post_configure_hook: scripts/post-configure-hook.sh
  hook_reason: "glib 2.38.2 Makefile uses -Werror, cannot patch at layer ①/②"
```

#### 方案对比

| 方案 | 可靠性 | 复杂度 | 推荐度 |
|------|--------|--------|--------|
| post-configure hook 脚本 | ✅ 高（显式、可审计） | 低 | ⭐⭐⭐ **首选** |
| PROGRESS.md 手动记录步骤 | ⚠️ 中（依赖人记忆） | 最低 | ⚠️ 仅用于极简情况 |
| 写入 Makefile 的 EXTRA_CFLAGS 覆盖 | ✅ 高（如果支持） | 中 | ⭐⭐ （需 configure 支持） |

---

## 4. CMake 适配

### 4.1 平台检测

在 `CMakeLists.txt` 中添加：

```cmake
# 检测 HarmonyOS
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OpenHarmony")
    set(OHOS TRUE)
    add_definitions(-D__OHOS__)
endif()
```

### 4.2 编译命令

```bash
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      ..
make -j$(nproc)
make install
```

## 5. 自定义 Perl Configure（OpenSSL 风格）

### 5.1 添加配置文件

创建 `Configurations/15-openharmony.conf`：

```perl
my %targets = (
    "openharmony" => {
        inherit_from     => [ "linux-generic32.0" ],
        template         => 1,
        cflags           => add("-D__OHOS__"),
        cppflags         => add("-D__OHOS__"),
        cxxflags         => add("-D__OHOS__"),
        thread_scheme    => "pthreads",
        dso_scheme       => "dlfcn",
        shared_target    => "linux-shared",
        shared_cflag     => "-fPIC",
    },
    "openharmony-aarch64" => {
        inherit_from     => [ "openharmony", "linux-aarch64" ],
    },
);
```

### 5.2 修改 Configure 脚本

添加自动检测逻辑：

```perl
# 检测 HarmonyOS
if ($target eq "" && -x "/system/bin/getprop") {
    my $sysname = `uname -s 2>/dev/null`;
    if ($sysname =~ m/harmonyos|openharmony/i) {
        $target = "openharmony-" . `uname -m`;
    }
}
```

### 5.3 编译命令

```bash
# OpenSSL 编译
./Configure --prefix=$HOME/usr/local \
            --openssldir=$HOME/usr/local/ssl \
            no-asm \
            openharmony-aarch64

make -j$(nproc)
make install
```

## 6. Makefile 直接修改

对于简单的 Makefile 项目，直接修改：

```makefile
# 添加编译器设置
CC = clang
AR = llvm-ar
RANLIB = llvm-ranlib

# 添加编译标志
CFLAGS += -fPIC -D__OHOS__

# 添加安装前缀
PREFIX ?= $(HOME)/usr/local
```

## 7. 构建系统对比

| 方面 | Autotools | CMake | Custom-Perl |
|------|-----------|-------|-------------|
| 学习曲线 | 中等 | 较高 | 低（OpenSSL 特有） |
| 平台检测 | config.guess | CMAKE_SYSTEM_NAME | Configure 脚本 |
| 三元组支持 | ✅ 原生 | ❌ 需手动 | ❌ 使用目标名 |
| 交叉编译 | ✅ 优秀 | ✅ 优秀 | ⚠️ 需配置 |
| 鸿蒙适配难度 | 中等 | 简单 | 中等 |

## 8. 常见问题

### 问题1：configure 检测到错误的三元组

**解决**：手动指定
```bash
./configure --host=aarch64-unknown-linux-ohos
```

### 问题2：CMake 找不到编译器

**解决**：显式指定
```bash
cmake -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++
```

### 问题3：OpenSSL Configure 无法识别系统

**解决**：直接指定目标
```bash
./Configure openharmony-aarch64
```

## 9. 测试原则

### 9.1 必须执行官方测试套件

> **核心原则**：编译完成后，必须执行官方测试套件，不能跳过。

**原因**：
1. 验证编译产物的正确性
2. 发现潜在的兼容性问题
3. 为后续用户提供可靠的参考

**测试命令**：

| 构建系统 | 测试命令 |
|----------|----------|
| Autotools | `make check` |
| CMake | `ctest` 或 `make test` |
| Makefile | `make test`（如有） |
| 自定义 | 查看项目文档 |

### 9.2 测试结果分类

测试失败时，需要区分两类问题：

| 类型 | 特征 | 示例 |
|------|------|------|
| **编译问题** | 功能本身不工作 | 链接错误、段错误、输出错误 |
| **环境兼容性问题** | 功能正常但测试框架不兼容 | BusyBox 缺少选项、PTY 不可用 |

**处理方式**：
- 编译问题：必须修复后重新编译
- 环境兼容性问题：在 manifest.yaml 和测试报告中记录，标记为"不影响核心功能"

### 9.3 测试报告模板

```markdown
# XXX 测试报告

## 测试结果汇总

| 测试项 | 结果 |
|--------|------|
| test1 | ✅ PASS |
| test2 | ❌ FAIL |

## 失败分析

### test2

**失败原因**: ...

**影响范围**: ...

## 结论

兼容性评级: 高/中/低
```

### 9.4 manifest.yaml 测试结果字段

```yaml
test_results:
  type: official  # official | manual | skipped
  total: 6
  passed: 5
  failed: 1
  note: |
    详细说明测试结果和失败原因
```

## 10. 特殊构建场景

### 10.1 automake 鸡生蛋问题

**问题**：编译 automake 自身时，make 过程需要调用尚未构建好的 automake 来重新生成 Makefile.in 文件，形成循环依赖。

**现象**：
- config.status 执行后 Makefile 中存在未替换的变量（如 `@am_AUTOCONF@`）
- make check 触发重新生成导致失败

**解决方案**：
1. 使用 automake 自带的 `gen-all.pl` 脚本手动生成所有模板文件
2. 手动 sed 修补残留变量（如 `@am_AUTOCONF@` → `autoconf`）
3. 手动 cp 安装到正确目录

### 10.2 无 32 位兼容层的软件

**问题**：部分软件（如 strace）默认启用 32 位兼容支持（m32 personality），在纯 aarch64 鸿蒙系统上无法编译。

**解决方案**：
```bash
# strace
./configure --disable-mpers

# 其他类似的软件，检查 configure --help 中是否有 32 位相关选项
./configure --help | grep -i "32\|m32\|multi\|personality"
```

**适用软件**：strace 6.19

### 10.3 automake 版本不匹配

**问题**：上游 tarball 要求 automake 版本高于系统安装的版本（如要求 1.17 但系统只有 1.16.5），或 configure 过程中 autotools 检测到时间戳不一致触发重生成。

**现象**：
```
configure.ac: error: requires automake >= 1.17, but 1.16.5 is installed
```

**解决方案**：

```bash
# 使用 /bin/true 绕过 autotools 工具调用
ACLOCAL="/bin/true" AUTOHEADER="/bin/true" AUTOMAKE="/bin/true" \
  ./configure --prefix=$HOME/usr/local
make -j1
```

**适用条件**：tarball 中已包含正确生成的 `Makefile.in` 文件。

**适用软件**：man-db 2.13.1

### 10.4 VPATH 构建避免 autotools 重生成

**问题**：某些 autotools 项目在 make 过程中会检测源码时间戳，如果比生成的 Makefile.in 更新，会尝试调用 autotools 重新生成，导致失败或无限循环。

**解决方案**：使用 VPATH（out-of-tree）构建，将源码和构建产物分离：

```bash
# 源码目录（保持只读，不修改时间戳）
$HOME/man-db-src/

# 构建目录（所有编译产物在这里）
$HOME/build-man-db/

cd $HOME/build-man-db
ACLOCAL="/bin/true" AUTOHEADER="/bin/true" AUTOMAKE="/bin/true" \
  ../man-db-src/configure --prefix=$HOME/usr/local
make -j1
make install
```

**优势**：
1. 不触碰源码目录的时间戳，避免触发 autotools 重生成
2. 源码和构建产物分离，方便多配置构建
3. 清理构建产物只需删除构建目录

**注意**：部分 autotools 项目的 `make` target 名称在 VPATH 下可能不同（如 `make mandb` vs `make src/mandb`），需要检查实际 Makefile。

**适用软件**：man-db 2.13.1

### 10.5 上游 config.guess 已含 HarmonyOS 但 config.sub 不完整

**问题**：部分较新的上游 tarball 的 `config.guess` 已包含 HarmonyOS 检测（`__OHOS__` 和 `*:HarmonyOS:*:*`），但 `config.sub` 缺少对应的 `ohos` 支持，导致三元组验证失败。

**诊断**：
```bash
grep -c "HarmonyOS\|__OHOS__" build-aux/config.guess  # > 0
grep -c "ohos" build-aux/config.sub                     # = 0 ← 缺失
```

**解决方案**：只需补丁 config.sub（添加 `ohos-linux` 匹配、OS 允许列表 `ohos*`、kernel-os 验证 `linux-ohos*`），不需要修改 config.guess。

**适用软件**：man-db 2.13.1（上游 config.guess 已有 HarmonyOS 支持）