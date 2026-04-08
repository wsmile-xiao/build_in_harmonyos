---
name: openharmony-compile-agent
description: 鸿蒙系统编译智能体——三方库预编译框架
version: 4.0.0
author: OpenHarmony PC Developer社区
permissions: 文件读写权限、Shell执行权限、网络访问权限
---

> **每次编译任务前先读本文档。** 本文档回答"怎么做"，KNOW_YOUR_WHY.md 回答"为什么"。

---

# 一、快速参考卡（AI 先看这里）

## 1.1 标准工作流：五步走（含独立测试）

```bash
# ═══ Step 1: 初始化（全自动，~30秒）═══
./scripts/init-build.sh <软件名> [<版本>] [--url=URL]
#   输出: .build-context-<name>-<ver>
#   完成: 下载/解压/检索历史/创建骨架/环境检查

# ═══ Step 2: 编译（唯一需要 AI 的步骤）═══
source .build-context-<name>-<ver>   # 加载上下文变量
cd $BUILD_SRC_DIR                   # 进入源码目录
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install
#   记录修改意图到 PROGRESS.md
#   触发安全弹窗确认
#   ⚠️ configure 可能需要 3-10 分钟（autotools 大量 conftest），不要提前中断！

# ═══ Step 2.5: 独立目录安装验证（⭐ 新增标准步骤）═══
#   目的：验证"原始 tarball + 补丁集"可独立复现（核心质量保证）
TEST_SRC="$TMPDIR/builds/<name>-<ver>-test"    # 干净解压
TEST_PREFIX="$TMPDIR/<name>-test-install"        # 独立前缀
#   ① 解压干净 tarball → ② 应用 patches/*.patch
#   ③ ./configure --prefix=$TEST_PREFIX && make && make install
#   ④ 功能回归测试（--version + 核心功能）
#   ⑤ 通过后才进入 finish-build.sh

# ═══ Step 3: 收尾（全自动，~30秒）═══
./scripts/finish-build.sh <软件名> <版本> success|partial|failed
#   完成: 补丁生成→归档收尾→**质量门禁(verify)**→归档校验→总结报告
#   ⚠️ verify-build.sh 在此步骤内自动调用，无需单独执行

# ═══ Step 4: 质量门禁复查（可选，~15秒）═══  ← 仅在需要单独复查时使用
./scripts/verify-build.sh <软件名> <版本>
#   4 道门禁: 二进制完整性 → 功能可用性 → 可移植性 → 档案完整性
#   输出: reports/quality-report.md + PASS/FAIL 判定
#   FAIL 则不能标记为 success，只能 partial 或 failed
#   ⚠️ 正常流程已在 Step 3 自动执行，此步骤仅用于补充验证

# ═══ Step 5: 预编译包制作（⭐ verify PASS 后必须执行）═══
#   按 packaging.md 10 步流程：清理→链接替换→依赖收集→RPATH→Strip→签名→权限→install.sh→tar.gz
#   交付物: {name}-{ver}-ohos-aarch64.tar.gz + debug.tar.gz + install.sh

# ═══ Step 5.5: 归档收口（⭐ 最终完成前必须执行）═══
#   清理临时文件 + 必填文件校验 + 信息一致性检查
#   ./scripts/finalize-archive.sh <软件名> <版本>
```

### configure 预期耗时参考

| 构建系统 | 典型软件 | 预期耗时 | 说明 |
|----------|---------|---------|------|
| autotools | 小工具(sed/grep) | 3-8 min | 大量 conftest 编译 |
| autotools | 大型(gcc/bash) | 10-20 min | 更多特性检测 |
| cmake | 一般项目 | 1-3 min | 较快 |
| meson | 一般项目 | <1 min | 最快 |

⚠️ **首次 configure 必须等完成**（用于触发安全弹窗确认）。timeout 建议：autotools ≥600s，其他 ≥300s。

**特殊情况**：
```bash
# 新软件（registry 无记录）→ 自动搜索 URL 或手动指定
./scripts/init-build.sh libnew 1.0 --url=https://...

# 会话中断后恢复
./scripts/init-build.sh --resume

# 只做补丁不重新编译
./scripts/refresh-patch.sh --auto <软件名> <版本>
```

## 1.2 十条铁律（违反任何一条都是 bug）

| # | 规则 | 正确做法 | 禁止 |
|---|------|---------|------|
| R1 | **参数最少化** | `./configure --prefix=$P && make` | 加 `--build/--host`/CFLAGS hack |
| R2 | **Phase 3 不生成 .patch** | 只改源码+记录到 PROGRESS.md | diff/sed 结果写文件 |
| R3 | **补丁只用 refresh-patch.sh** | `refresh-patch.sh --auto` | 手动 diff/AI 写 patch |
| R4 | **危险库必须静态编译** | ncurses `--without-shared` | 编译共享库导致系统崩溃 |
| R5 | **软链接必须验证可执行 + 禁止 ln -sf** | `verify-symlinks.sh` + `rm -f && ln -s` | 只检查 `-L` 存在性 / `ln -sf` 覆盖 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h（源码层） | sed 改 configure/Makefile/Makefile.in（不可复现） |
| R7 | **安全弹窗必须先触发再测试** | make install 后 `find $DEFAULT_PREFIX/bin -exec {} --version \;` 扫一遍 | 直接跑 make check 不触发弹窗→进程被杀→假阴性 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫 / 保持上游风格 / 追加平台分支 | 删跨平台代码 / 硬编码路径 / 改原逻辑流 / 偏离代码风格 |
| R9 | **质量门禁 FAIL 禁止标 success** | verify-build.sh 非零 → partial 或 failed | 产物有问题仍标记成功分发 |
| R10 | **临时文件必须用 $TMPDIR** | 所有 tmp 文件操作使用 `$TMPDIR` 或 `$HOME/tmp` | 硬编码 `/tmp`（鸿蒙 /tmp 只读，见 E002） |

### AI 执行风格规范（⭐ 新增）

> **原则：在鸿蒙 toybox ash 环境下，复杂 shell 脚本是地雷区。保持简单。**

#### 测试脚本原则

| ✅ 推荐 | ❌ 禁止 |
|---------|--------|
| 每个测试一条独立的 `[ ] && echo OK \|\| echo FAIL` | 单次 tool_call 写 >30 行复杂 shell 脚本 |
| 变量先赋值再使用，避免管道内嵌套命令替换 | heredoc（与 `curl \| sh` 冲突，toybox ash 支持差） |
| 用 `$TMPDIR/$HOME/tmp` 替代 `/tmp`（R10） | `for desc cmd exp in ...` 多变量循环 + 引号嵌套 |
| `grep -F` 做固定字符串匹配（防正则元字符陷阱） | grep 不加 `-F` 匹配含 `()` `[]` `$` 的输出 |
| `case "$var" in *pattern*)` 做 shell 原生模式匹配 | 复杂 awk/sed 管道做简单字符串判断 |
| 逐条顺序执行，每步可独立验证 | 一次性提交大量命令，出错后难以定位 |

#### configure/make 长时间命令

```bash
# ✅ 正确：给足够 timeout，不提前中断
cd $BUILD_SRC_DIR && ./configure --prefix=$DEFAULT_PREFIX 2>&1 | tail -3
#   autotools 项目 timeout=600s, 其他 timeout=300s

# ❌ 错误：频繁中断重启（浪费每次 3-10 分钟的 conftest 编译）
```

### R8 详细说明：源码修改"四不"准则

> **核心原则：你的修改对非鸿蒙平台必须是透明的。**
> **检验方法：去掉所有 `#ifdef __OHOS__` 块后，上游代码应与原始 tarball 一模一样。**

| 不 | 含义 | 错误示例 | 正确做法 |
|----|------|---------|---------|
| **不破坏上游逻辑** | 不删除/反转/改变原有代码行为 | 删除某个 `if (linux)` 分支 | 用 `#elif defined(__OHOS__)` 追加新分支 |
| **不破坏跨平台兼容性** | 不删除其他平台的已有适配 | 删掉 `#ifdef _WIN32` 块因为它"用不到" | 保留所有平台守卫，在旁边加 `__OHOS__` |
| **不绕过鸿蒙标识机制** | 不硬编码平台特征 | `if (strstr(path, "/usr/local") != NULL)` | `#ifdef __OHOS__` + config.guess/sub 统一处理 |
| **不偏离上游代码风格** | 缩进/命名/注释风格与项目一致 | 项目 4 空格你用 tab | 读周边 50 行代码，保持一致 |

**常见反模式（绝对禁止）**：
```bash
# ❌ 硬编码路径 — 换设备就挂
sed -i 's|/usr/bin|/data/local/tmp/usr/bin|g' Makefile

# ❌ 删除跨平台检测 — 破坏 macOS/Windows 构建
sed -i '/case.*darwin/d' config.sub

# ❌ 条件注入 — 无法 upstream
echo "#define OHOS_FIX 1" >> config.h

# ✅ 正确方式：平台守卫 + 可 upstream
# 在 configure.ac 中追加:
#   AC_CHECK_DECLS([__OHOS__], [ohos_fix=1])
# 在 C 代码中:
#   #if defined(__OHOS__)
#   /* 鸿蒙特定修复 */
#   #endif
```

## 1.3 决策树

```
遇到一个新三方库？
│
├─ registry 有记录？
│   ├─ 是 → ./scripts/init-build.sh <name> <ver>     （全自动）
│   └─ 否 → 有 URL？
│       ├─ 是 → ./scripts/init-build.sh <name> <ver> --url=URL
│       │        → 自动注册到 registry（下次直接命中）
│       └─ 否 → ./scripts/search-download-url.sh <name> <ver>
│                → 从候选列表选 URL → 重试上一步
│
configure 失败？
│
├─ 缺依赖？ → 查 dependencies.md 编译顺序 → 先编依赖
├─ 平台不识别？ → 改 config.guess/sub（见 build-systems.md §3.1）
├─ conftest pipe 问题？ → configure 中 `\| cat` 修复
└─ 其他？ → 查 error-patterns.md → 按 E编号查找
```

---

# 二、核心流程详解

## Step 1: init-build.sh — Phase 0→2 全自动

> **AI 不需要手动执行 Phase 0/1/2 的任何步骤。** 这条命令完成全部。

### 调用方式

```bash
# 标准用法（registry 有记录时全自动）
./scripts/init-build.sh sed 4.9

# 自定义 URL（首次遇到新软件时）
./scripts/init-build.sh libnew 2.0 --url=https://example.com/libnew-2.0.tar.gz

# 跳过下载（源码已存在时）
./scripts/init-build.sh sed 4.9 --no-download

# 恢复中断的会话
./scripts/init-build.sh --resume
```

### 内部完成的 8 个步骤

| 步骤 | 内容 | 失败时 |
|------|------|--------|
| [1/8] | 查询 software-registry.yaml 元数据 | 未命中 → 降级搜索 |
| [2/8] | 确定 URL（注册表 / 自定义 / 搜索） | 无 URL → 输出候选列表 |
| [3/8] | 下载 tarball + HTML 页面检测 | 失败 → 尝试备用 URL |
| [4/8] | 解压到 $TMPDIR/builds/<name>-<ver>/ | 失败 → 检查格式 |
| [5/8] | 检索 archives/ 历史档案 | 无历史 → 标记首次编译 |
| [6/8] | 创建/恢复档案骨架 (init-archive.sh) | 失败 → 手动创建最小骨架 |
| [7/8] | 环境检查 (check-env.sh) | 缺变量 → 提示设置 |
| [8/8] | 输出 .build-context 文件 | — |

### 输出：.build-context 文件

init-build.sh 成功后输出 `.build-context-<name>-<ver>`，包含所有路径变量。AI 在 Step 2 中 source 它即可获得完整上下文。

**关键变量**：
```
BUILD_SOFTWARE    # 软件名
BUILD_VERSION      # 版本号
BUILD_SYSTEM       # 构建系统 (autotools/cmake/meson/...)
BUILD_SRC_DIR      # 源码目录绝对路径
BUILD_ARCHIVE_DIR   # 归档目录绝对路径
BUILD_URL          # 下载 URL
BUILD_HISTORY_FOUND # 是否有历史档案 (true/false)
DEFAULT_PREFIX     # ⭐ 唯一权威的安装前缀路径（所有脚本统一使用）
```

### 变量命名规范（⭐ C01 统一）

> **消除歧义：整个管线中，安装前缀只用 `$DEFAULT_PREFIX` 一个变量名。**

| 变量名 | 含义 | 谁设置 | 谁使用 | 作用域 |
|--------|------|--------|--------|--------|
| **`DEFAULT_PREFIX`** | **唯一权威**的安装前缀路径 | `init-build.sh` export + 写入 .build-context | **所有脚本**（verify-build.sh, package.sh, AI Phase 3） | 全局 |
| `PKGDIR` | 打包工作目录（package.sh 内部临时目录） | `package.sh` 设置 | 仅 `package.sh` 内部 | 局部 |

**历史遗留**：旧文档/代码中可能出现 `$PREFIX`，等同于 `$DEFAULT_PREFIX`（兼容别名），新代码统一使用 `$DEFAULT_PREFIX`。

### registry 自动增长机制

当 registry 未命中但提供了 `--url` 时，脚本**自动将软件信息追加到 `software-registry.yaml`**：
- 推断构建系统（从 URL 域名）
- 推断 tar 格式（从 URL 后缀）
- 标记 `category: auto-discovered`
- 下次再编同一软件直接命中缓存

## Step 2: AI 编译执行 — Phase 3（唯一智能步骤）

> **这是整个流程中唯一需要 AI 判断的环节。** 其余全部自动化。

### 2.1 开始编译前的准备

```bash
# ① 加载上下文
source .build-context-<name>-<ver>

# ② 进入源码目录
cd $BUILD_SRC_DIR

# ③ 如有历史补丁，应用它们
if [ "$BUILD_HISTORY_FOUND" = "true" ]; then
    for p in $BUILD_ARCHIVE_DIR/patches/*.patch; do
        patch -p1 < "$p"
    done
fi

# ④ 识别构建系统（如需要）
./scripts/detect-build-system.sh .  # 可选，context 已含 BUILD_SYSTEM
```

### 2.2 执行编译

```bash
# Autotools 项目
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install

# CMake 项目
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX .. && make && make install

# Meson 项目
meson setup builddir --prefix=$DEFAULT_PREFIX && ninja -C builddir && ninja -C builddir install

# Makefile 项目（无 configure）
make PREFIX=$DEFAULT_PREFIX && make PREFIX=$DEFAULT_PREFIX install
```

**⚠️ P0 参数最少化**：理想状态只需 `--prefix`。如果必须加额外参数（`--build/--host`/`--without-shared`/CFLAGS hack），记录到 PROGRESS.md 并在 manifest.yaml `build_cleanliness` 字段标注为技术债务。

### 2.2.1 make check / make test（⭐ 标准步骤）

> **make install 之后、finish-build 之前，必须执行软件自带的测试套件。**

```bash
# Autotools 项目（首选 make check，fallback 到 make test）
make -j1 check 2>&1 | tail -20    # 记录结果到 reports/test-report.md
# 或: make -j1 test 2>&1 | tail -20

# CMake 项目
ctest --output-on-failure 2>&1 | tail -20

# Meson 项目
meson test -C builddir 2>&1 | tail -20
```

**测试结果处理**：

| 结果 | 处理方式 |
|------|---------|
| **全通过 (PASS)** | 记录到 `reports/test-report.md`，继续下一步 |
| **部分失败但核心功能 OK** | 分析失败原因 → 平台限制(E051/E046等)则记录并继续；真正的 bug 则修复后重测 |
| **全部失败或 core dump** | 检查是否漏触发安全弹窗(R7) → 重新触发后再跑 |

**⚠️ 鸿蒙特有限制**（导致部分测试预期失败，不阻塞发布）：
- E046: chmod() 不生效 → 权限相关测试失败
- E051: 未实现 syscall → setreuid/chroot 等测试 crash
- `/tmp` 只读（E002）→ 依赖 /tmp 的测试失败
- SELinux 域转换 → 子进程执行 SDK 工具失败

**关键原则**：测试套件的目的是**发现真正的功能回归**，不是追求 100% 通过率。平台限制导致的预期失败应记录原因但不阻塞流程。

### 2.3 错误处理与恢复

#### 错误分类与标准对策

| 阶段 | 常见错误 | 标准对策 |
|------|---------|---------|
| **configure** | `command not found: xxx` | 缺工具 → 安装或设 ACLOCAL=/bin=true 绕过 |
| **configure** | `cannot run test program` | conftest pipe 问题 → `\| cat` 修复 |
| **configure** | `invalid host: aarch64-unknown-linux-ohos` | config.guess/sub 未识别 → 打补丁 |
| **compile** | `error: xxx.h: No such file` | 缺头文件 → 查依赖链/CFLAGS 加 -I |
| **compile** | `warning: -Werror` | 警告变错误 → CFLAGS 加 -Wno-error 或改 configure.ac |
| **link** | `undefined reference to xxx` | 缓库 → LDFLAGS 加 -lxxx 或查 NEEDED |
| **install** | `symlink: File exists` | HMDFS 限制 → 用 wrapper 脚本或 cp 替代 |

#### 失败恢复操作序列

```
configure 失败:
  1. make distclean          # 清理旧配置
  2. 查 error-patterns.md    # 按错误信息匹配已知方案
  3. 修改源码/补丁/configure
  4. 重新 ./configure ...

编译失败 (make):
  1. 读最后 20 行错误         # 定位具体文件和行号
  2. 修复该文件              # 最小改动原则
  3. make -j1                 # 单线程重新编译（避免并行干扰）
  4. 如果还不行 → make clean && make -j1

安装失败 (make install):
  1. 检查是否是软链接问题      # verify-symlinks.sh
  2. 是 → wrapper 脚本替代
  3. 不是 → 检查权限/磁盘空间
```

### 2.4 Phase 3 补丁管线规则（⚠️ 强制）

**Phase 3 绝对禁止生成 .patch 文件。**

Phase 3 的职责只有两件事：
1. **修改源码**解决编译问题
2. **在 PROGRESS.md 记录**每个修改的意图

原因：Phase 3 源码处于频繁试错状态，此时生成的补丁是中间态。
补丁生成**唯一入口**是 Phase 4 的 `refresh-patch.sh --auto`。

**允许的操作**：
- ✅ `sed` / 直接编辑源码（解决编译问题）
- ✅ 创建 post-configure hook 脚本（§3.9）
- ✅ 在 PROGRESS.md「源码修改清单」中记录

**禁止的操作**：
- ❌ 生成任何 `.patch` 文件
- ❌ 手动写 diff 内容到文件
- ❌ AI 生成补丁文本写入文件
- ❌ copy 之前的 `.patch` 文件

### 2.5 实时知识提取

每解决一个问题后，立即判断：

```
Q1: 此问题只与本软件有关？
    → 是：只记录到 PROGRESS.md
    → 否（其他软件也可能遇到）：
        Q2: 与平台机制相关？（musl/SELinux/文件系统/内核）
            → 是：立即更新 knowledge/（L1 平台真理）
            → 否：是构建系统模式？（autotools/cmake 通用问题）
                → 是：更新 knowledge/（L2 模式经验）
                → 否：标记 "⏳ 待评估"（Phase 4 处理）
```

### 2.6 安全弹窗验证

鸿蒙系统首次执行非系统二进制会弹安全确认框，超时未点则进程被杀。

```bash
# make install 后立即触发
find $HOME/usr/local/bin -type f -exec {} --version \; 2>/dev/null || true

# make check 前确保已完成弹窗确认
```

### 2.7 更新 PROGRESS.md

每解决一个问题后**立即**更新 PROGRESS.md：
- 当前阶段和时间
- 错误信息 + 根因 + 解决方案
- 源码修改清单（表格：文件 | 原因 | 方式 | 补丁状态）

### 2.8 Phase 2.5: 独立目录安装验证（⭐ 必须执行）

> **目的**：验证编译产物可以在干净的独立目录中正确安装和运行，排除对构建环境的隐性依赖。
> **时机**：Phase 2 (`make install` 成功) 之后、`finish-build.sh` 之前。
> **重要性**：这是保证"可复现性"的核心步骤——没有它，你无法确认补丁集 + tarball 能在另一台机器上产出相同结果。

#### 前置条件

| 条件 | 检查方式 |
|------|---------|
| Phase 2 编译成功 | `make install` 已执行且 `$DEFAULT_PREFIX` 下有文件 |
| 原始 tarball 存在 | `.build-context-*` 中 `BUILD_URL` 可用或 `archives/` 有源码 |
| 补丁集完整 | `archives/.../patches/000*.patch` 存在 |
| 磁盘空间足够 | 至少 200MB 可用空间（用于独立编译） |

#### Step 2.5.1: 创建独立测试目录

```bash
# 使用 $TMPDIR 遵守 R10（禁止硬编码 /tmp）
TEST_SRC="${TMPDIR:-$HOME/tmp}/builds/${SOFTWARE}-${VERSION}-test"
TEST_PREFIX="${TMPDIR:-$HOME/tmp}/test-install-${SOFTWARE}-${VERSION}"

# 清理旧残留（防止上次中断的脏数据影响结果）
rm -rf "$TEST_SRC" "$TEST_PREFIX"
mkdir -p "$TEST_SRC" "$TEST_PREFIX/bin" "$TEST_PREFIX/lib" "$TEST_PREFIX/include"

echo "[2.5.1] 独立测试目录已创建:"
echo "  TEST_SRC=$TEST_SRC"
echo "  TEST_PREFIX=$TEST_PREFIX"
```

#### Step 2.5.2: 解压干净源码 + 应用补丁

```bash
echo "[2.5.2] 解压原始 tarball..."

# 从 manifest.yaml 获取源码 URL（最可靠）
TAR_URL=$(grep "^source_url:" "${BUILD_ARCHIVE_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')

# 或从 build-context 获取
if [ -z "$TAR_URL" ] && [ -f ".build-context-${SOFTWARE}-${VERSION}" ]; then
    TAR_URL=$(grep "^BUILD_URL=" ".build-context-${SOFTWARE}-${VERSION}" | cut -d= -f2- | tr -d '"')
fi

if [ -n "$TAR_URL" ]; then
    # 根据扩展名选择解压方式
    case "$TAR_URL" in
        *.tar.xz)  curl -fsSL "$TAR_URL" 2>/dev/null | tar xJf - -C "$TEST_SRC" ;;
        *.tar.gz|*.tgz) curl -fsSL "$TAR_URL" 2>/dev/null | tar xzf - -C "$TEST_SRC" ;;
        *.tar.bz2) curl -fsSL "$TAR_URL" 2>/dev/null | tar xjf - -C "$TEST_SRC" ;;
        *)         curl -fsSL "$TAR_URL" -o "${TEST_SRC}/dl.tar" 2>/dev/null && tar xf "${TEST_SRC}/dl.tar" -C "$TEST_SRC" ;;
    esac
    echo "  ✅ 解压完成"
else
    echo "  ⚠️ 无法获取 tarball URL，尝试复制现有源码..."
    cp -a "$BUILD_SRC_DIR" "${TEST_SRC}/$(basename "$BUILD_SRC_DIR")"
fi

# 找到解压出的顶层目录
EXTRACTED_DIR=$(ls -1d "$TEST_SRC"/*/ 2>/dev/null | head -1 | sed 's:/$::')
if [ -z "$EXTRACTED_DIR" ]; then
    echo "[FAIL] 解压失败：未找到源码目录"
    exit 1
fi
echo "  源码目录: $EXTRACTED_DIR"

# 应用所有补丁
echo "[2.5.2] 应用补丁集..."
PATCH_COUNT=0
for p in "${BUILD_ARCHIVE_DIR}"/patches/000*.patch; do
    [ -f "$p" ] || continue
    if patch -p1 --dry-run -i "$p" -d "$EXTRACTED_DIR" >/dev/null 2>&1; then
        patch -p1 < "$p" -d "$EXTRACTED_DIR" >/dev/null 2>&1
        PATCH_COUNT=$((PATCH_COUNT + 1))
    else
        echo "  ⚠️ 补丁 $(basename $p) dry-run 失败，跳过"
    fi
done
echo "  ✅ 已应用 ${PATCH_COUNT} 个补丁"
```

#### Step 2.5.3: 独立目录 configure + make + make install

```bash
echo "[2.5.3] 独立目录编译安装..."

cd "$EXTRACTED_DIR"

# 使用与 Phase 2 相同的 configure 参数（保持一致性）
# 注意 prefix 使用独立的 TEST_PREFIX
./configure --prefix="$TEST_PREFIX" 2>&1 | tail -3
CONFIGURE_RC=$?

if [ $CONFIGURE_RC -ne 0 ]; then
    echo "[FAIL] 独立目录 configure 失败 (rc=${CONFIGURE_RC})"
    echo "  → 这意味着产物不可在其他环境复现！需要排查原因"
    exit 1
fi

make -j1 2>&1 | tail -5
MAKE_RC=$?

if [ $MAKE_RC -ne 0 ]; then
    echo "[FAIL] 独立目录 make 失败 (rc=${MAKE_RC})"
    exit 1
fi

make install 2>&1 | tail -3
INSTALL_RC=$?

if [ $INSTALL_RC -ne 0 ]; then
    echo "[FAIL] 独立目录 make install 失败 (rc=${INSTALL_RC})"
    exit 1
fi

echo "  ✅ 独立编译安装成功"
```

> **⚠️ 如果 Makefile 不支持 DESTDIR**（常见于简单 Makefile 项目）：
> ```bash
> # fallback 方案：直接从已安装目录复制
> cp -a "$DEFAULT_PREFIX/bin/"* "$TEST_PREFIX/bin/" 2>/dev/null || true
> cp -a "$DEFAULT_PREFIX/lib/"* "$TEST_PREFIX/lib/" 2>/dev/null || true
> cp -a "$DEFAULT_PREFIX/include/"* "$TEST_PREFIX/include/" 2>/dev/null || true
> ```

#### Step 2.5.4: 文件完整性验证 + 运行时功能回归测试

```bash
echo "[2.5.4] 文件完整性检查..."

# 统计安装产物
BIN_COUNT=$(find "$TEST_PREFIX/bin" -type f 2>/dev/null | wc -l | tr -d ' ')
LIB_COUNT=$(find "$TEST_PREFIX/lib" -type f 2>/dev/null | wc -l | tr -d ' ')
INC_COUNT=$(find "$TEST_PREFIX/include" -type f 2>/dev/null | wc -l | tr -d ' ')

echo "  二进制文件: ${BIN_COUNT}"
echo "  库文件:     ${LIB_COUNT}"
echo "  头文件:     ${INC_COUNT}"

if [ "$BIN_COUNT" -eq 0 ] && [ "$LIB_COUNT" -eq 0 ]; then
    echo "[FAIL] 独立安装目录为空！"
    exit 1
fi

echo ""
echo "[2.5.4] 运行时功能回归测试..."

# 设置独立环境变量（关键：使用 TEST_PREFIX 而非 DEFAULT_PREFIX）
export LD_LIBRARY_PATH="$TEST_PREFIX/lib:${LD_LIBRARY_PATH:-}"
export PATH="$TEST_PREFIX/bin:${PATH}"

PASS_COUNT=0; FAIL_COUNT=0; WARN_COUNT=0

# 测试每个二进制的 --version（与 G2 类似但更轻量）
for cmd in "$TEST_PREFIX/bin"/*; do
    [ -x "$cmd" ] || continue
    name=$(basename "$cmd")
    
    # 跳过脚本类 wrapper
    head -1 "$cmd" 2>/dev/null | grep -q "^#!" && continue
    
    output=$("$cmd" --version 2>&1 | head -1)
    if [ -n "$output" ]; then
        echo "  ✅ $name: $output"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        # 尝试 --help 作为 fallback
        output=$("$cmd" --help 2>&1 | head -1)
        if [ -n "$output" ]; then
            echo "  ⚠️ $name: 无 --version，--help 有输出"
            WARN_COUNT=$((WARN_COUNT + 1))
        else
            echo "  ❌ $name: 无可用输出"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    fi
done

echo ""
echo "  回归测试结果: ${PASS_COUNT} 通过 / ${FAIL_COUNT} 失败 / ${WARN_COUNT} 警告"

# 恢复环境变量（避免污染后续步骤）
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH#$TEST_PREFIX/lib:}"
export PATH="${PATH#$TEST_PREFIX/bin:}"
```

#### Step 2.5.5: 清理或保留策略

```bash
echo "[2.5.5] 清理独立测试目录..."

# 默认行为：清理以节省空间（R10: 使用 $TMPDIR）
if [ "${KEEP_TEST_DIR:-0}" != "1" ]; then
    rm -rf "$TEST_SRC" "$TEST_PREFIX"
    echo "  ✅ 已清理独立测试目录（节省空间）"
    echo "  💡 如需保留用于调试: KEEP_TEST_DIR=1 ./scripts/prep-test.sh"
else
    echo "  📁 保留测试目录（KEEP_TEST_DIR=1）:"
    echo "     TEST_SRC=$TEST_SRC"
    echo "     TEST_PREFIX=$TEST_PREFIX"
fi

echo ""
echo "════════════════════════════════════════"
echo "  Phase 2.5 结果: PASS → 可进入 finish-build.sh"
echo "════════════════════════════════════════"
```

#### Phase 2.5 判定标准

| 结果 | 条件 | 后续操作 |
|------|------|---------|
| **Phase 2.5 判定: PASS** | configure + make + install 全部成功 + 回归测试无失败 | 进入 Step 3 `finish-build.sh success` |
| **Phase 2.5 判定: PARTIAL** | 安装成功但部分功能测试失败 | → `finish-build.sh partial`，分析失败原因→平台限制则记录并继续；真正的 bug 则修复 |
| **Phase 2.5 判定: FAIL** | configure/make/install 任一步骤失败 | → `finish-build.sh failed`，**必须修复**——意味着产物不可复现 |

#### 与 prep-test.sh 的关系

`prep-test.sh` 负责 Phase 2.5 的**前置准备**（弹窗触发 + 环境设置），而 Phase 2.5 本身的**完整流程**（解压→编译→安装→测试）由 AI 在本节指导下手动执行。两者关系：

```
make install (Phase 2 完成)
    │
    ├── ./scripts/prep-test.sh              ← 触发弹窗 + 设置 MAKEFLAGS=-j1
    │
    └── Phase 2.5 本流程 (§2.8)             ← AI 手动执行 5 步独立验证
        │
        └── 通过 → ./scripts/finish-build.sh  ← 自动收尾
```

## Step 3: finish-build.sh — Phase 4 全自动

> **编译成功后一条命令完成所有收尾工作。**

```bash
./scripts/finish-build.sh <软件名> <版本> success|partial|failed
```

### 内部执行的 5 个步骤

| 步骤 | 脚本 | 内容 | 失败处理 |
|------|------|------|---------|
| [1/5] | refresh-patch.sh --auto | 从原始 tarball diff → per-file 补丁 → 格式校验 → dry-run → hash 绑定 → 写入 manifest | 失败跳过，继续归档 |
| [2/5] | close-archive.sh | 更新 status → 关闭 PROGRESS.md → 检查知识条目 | 失败则退出(2) |
| [3/5] | **verify-build.sh** | **质量门禁 G1-G4（二进制/功能/可移植/档案）** | **非阻塞：失败降级状态，不中断管线** |
| [4/5] | finalize-archive.sh | 清理+校验+一致性检查+RELEASENOTE | 失败非致命 |
| [5/5] | gen_summary.py | 重新生成 SUMMARY.md | 失败非致命 |

### 状态选择指南

> **统一状态值体系**：整个项目仅使用以下三个状态值，所有脚本和文档必须一致。

| 状态 | 含义 | 使用场景 |
|------|------|---------|
| `success` | 编译+测试+验证全通过 | finish-build.sh, close-archive.sh, PROGRESS.md |
| `partial` | 编译成功但部分测试/验证失败 | 同上（标注限制后仍可分发） |
| `failed` | 编译失败且无法绕过 | init-build.sh --resume 判断，跳过打包 |

**已废弃的状态值**（历史遗留，不得在新代码中使用）：
- ~~`pass`/``fail``~~ → 仅用于 G1-G4 单项门禁判定（PASS/FAIL-Gx），不作为整体状态
- ~~`completed`/`closed`/`tested`~~ → 幽灵状态，已从所有脚本清除

**状态转换规则**（finish-build.sh 内部自动执行）：
```
输入状态 ──[verify 通过]──→ 输出状态
success  ─────────────────→ success （不变）
partial  ─────────────────→ partial （不变）
failed   ─────────────────→ partial （升级：验证通过至少是 partial）

输入状态 ──[verify 失败]──→ 输出状态
success  ─────────────────→ partial  （降级）
partial  ─────────────────→ failed  （降级）
failed   ─────────────────→ failed  （不变）
```

## Step 4: verify-build.sh — 质量门禁（必须）

> **编译成功 ≠ 产物可用。** 这是交付前的最后一道关卡。
> **⚠️ 此步骤已在 finish-build.sh Step 3 中自动调用，通常无需手动执行。**
> 手动执行适用于：单独复查、finish 之后补充验证、调试门禁逻辑。

```bash
./scripts/verify-build.sh <软件名> <版本>
# 或由 finish-build.sh Step 3 自动调用（传入 --archive-dir）
```

### 4 道门禁

| 门禁 | 检测内容 | 失败后果 |
|------|---------|---------|
| **G1 二进制完整性** | ELF 可执行 / ldd 无缺依赖 / file 正确 | 产物在目标设备无法运行 |
| **G2 功能可用性** | --version 正常 / 核心功能端到端测试 | 编译通过但功能异常 |
| **G3 可移植性** | RPATH=\$ORIGIN / ELF 签名有效 | 其他鸿蒙设备上不可用 |
| **G4 档案完整性** | man page / .pc 文件 / 补丁可 rebuild / manifest 完整 | 无法复现或被依赖方无法使用 |

### 判定标准

```
PASS     → 全部通过 → 标记 success，可分发
PASS-WARN → 通过但 >10 警告 → 可分发但需关注
FAIL-Gx  → 对应门禁失败 → 只能 partial 或 failed，修复后重验
```

### 输出

- `reports/quality-report.md` — 详细报告
- exit 0 = 通过, exit 1 = 失败

### Step 5: 预编译分发包（⭐ verify PASS 后必须执行）

> **时机**：verify-build.sh PASS 之后（确保产物质量合格才打包）。
> **所有编译成功（status=success 或 partial）的软件都必须制作预编译包。**
> 只有 status=failed 才跳过。

#### 触发条件

| 状态 | 是否必须打包 | 说明 |
|------|------------|------|
| `success` | ✅ **必须** | 编译通过 + 测试通过 + 补丁完整 |
| `partial` | ✅ **必须** | 编译通过但部分功能不可用（标注限制后仍可分发） |
| `failed` | ❌ 跳过 | 编译失败，无产物可打包 |

#### 执行流程

按 `knowledge/packaging.md` 10 步标准流程：

```
Step 1:  安装到独立目录
Step 2:  清理缓存和非必要文件
Step 3:  符号链接替换（wrapper/cp）
Step 4:  收集外部依赖库到 lib/external/
Step 5:  设置 RPATH（$ORIGIN 相对路径）
Step 6:  Strip Debug 符号 + 分离保存
Step 7:  ELF 签名（adhoc self-sign）
Step 8:  统一修复执行权限（必做！）
Step 9:  创建 install.sh（单独托管 gitcode，不打包进 tar.gz）
Step 10: 打包干净 tar.gz + 安装验证
```

#### 交付物（2 个 tar.gz + 1 个软件级 install.sh）

```
archives/{首字母}/{软件名}/
├── install.sh                                # 安装脚本（软件级，参数化: sh -s -- <ver>）
├── RELEASENOTE.md                             # 发布说明（软件级）
│
└── {版本}/packaging/
    ├── {name}-{ver}-ohos-aarch64.tar.gz        # Release 制品（干净二进制，已 strip）
    └── {name}-{ver}-ohos-aarch64-debug.tar.gz   # Debug 符号包（必须）
```

用户安装：`curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/{name}/install.sh | sh -s -- {ver}`

## Step 5.5: 归档收口（⭐ 最终完成前必须执行）

> **时机**：Step 5（预编译包制作）完成之后、`attemptCompletion(success)` 之前。
> **目的**：确保归档目录干净、完整、一致，可以安全关闭。

### 为什么需要独立的收口步骤？

```
整个编译过程中产生的文件:
  ✅ 正式产物: manifest.yaml / PROGRESS.md / README.md / patches/*.patch
  ✅ 正式产物: packaging/*.tar.gz / packaging/install.sh
  ⚠️ 临时文件: *.tmp (refresh-patch 中断残留) / .bak (编辑备份)
  ⚠️ 过时数据: 旧 test-report.md (重编译前) / 旧 debug 符号
  ❌ 不一致: PROGRESS 写 success 但 manifest 写 compiling

问题: init-archive.sh 策略是"保留一切"（为了复用旧信息）
结果: 重编译后目录里混合了新旧数据，需要统一清理+校验
```

### 执行方式

```bash
./scripts/finalize-archive.sh <软件名> <版本>
```

### 内部执行的 4 个阶段

| 阶段 | 内容 | 失败处理 |
|------|------|---------|
| **[1] 清理** | 删除 `*.tmp`、`.bak`、debug/ 残留文件 | 无则跳过 |
| **[2] 必填校验** | 6 个必填项存在性 + 内容非空模板 + packaging 交付物完整性 | 缺失 → exit 2 |
| **[3] 一致性检查** | manifest vs PROGRESS 状态一致 / 补丁数量匹配 / 对话记录存在 | 警告但不阻塞 |
| **[4] 最终报告** | 输出汇总：补丁数/报告数/打包数/问题数 | 通过 → 可安全关闭 |

### 必填文件清单

| 文件 | 最小行数 | 说明 |
|------|---------|------|
| `manifest.yaml` | >10 行 | 元数据（init-archive 有内容则保留） |
| `README.md` | >10 行 | 编译指导 + 适配原因（版本级） |
| `PROGRESS.md` | >15 行 | 进展 + 对话记录（断点续传，版本级） |
| `RELEASENOTE.md` | >15 行 | 发布说明（软件级，finalize-archive 自动生成） |
| `install.sh` | 文件存在 | 安装脚本（软件级，参数化: sh -s -- <ver>） |
| `patches/` | 目录存在 | 补丁目录 |
| `reports/` | 目录存在 | 报告目录 |
| `packaging/*-ohos-aarch64.tar.gz` | 文件存在 | release 包（success/partial 时） |
| `packaging/*-debug.tar.gz` | 文件存在 | debug 包（必须） |
| `install.sh`（软件级） | 文件存在 | 安装脚本（参数化） |

### 一致性检查项

| 检查项 | 方法 | 允许差异 |
|--------|------|---------|
| 状态一致性 | grep status: manifest vs PROGRESS | 不允许 |
| 补丁数量 | manifest patches_applied vs 磁盘 *.patch 数 | 不允许 |
| 对话记录 | PROGRESS.md 中 `### 对话 #N` 出现次数 | 至少 1 轮 |

### 与 init-archive.sh 的分工

| 脚本 | 时机 | 策略 | 删除文件？ |
|------|------|------|----------|
| `init-archive.sh` | 编译开始前 | **保留**已有内容，只创建缺失骨架 | 否（除非 --clean） |
| `finalize-archive.sh` | 全部完成后 | 清理垃圾 + 校验 + 报告 | 是（*.tmp/.bak/不一致） |

### --clean 模式（完全重置）

当需要**丢弃所有旧补丁和打包产物重新开始**时：

```bash
# 方式 A: init 时指定 --clean
./scripts/init-build.sh <软件名> <版本> --clean

# 方式 B: 手动清空后重新 init
rm -rf archives/<首字母>/<软件名>/<版本>/patches/*
rm -rf archives/<首字母>/<软件名>/<版本>/packaging/*
./scripts/init-build.sh <软件名> <version>
```

---

# 三、核心规范

## 3.1 P0 参数最少化原则

**目标命令**：`./configure --prefix=$DEFAULT_PREFIX && make && make install`（零额外参数）

超出 `--prefix` 和软件自身选项的参数 = 技术债务。

| 参数类型 | 是否应该存在 | 消除方法 |
|---------|-------------|---------|
| `--prefix=$DEFAULT_PREFIX` | ✅ 必须 | — |
| 软件自身选项（如 `--with-internal-glib`） | ✅ 正常 | — |
| 平台约束（如 `--without-shared`） | ⚠️ 记录为债务 | 见 dependencies.md |
| `--build/--host/--target` | ❌ 应消除 | 完善 config.guess/sub |
| `-Wno-error` 等 CFLAGS hack | ❌ 应消除 | 在 configure.ac 加 `*ohos*` 分支 |
| `sed` 操作生成文件 | ❌ 绝对禁止 | 改为正式 .patch 补丁 |

**每次编译后在 manifest.yaml 记录**：
```yaml
build_cleanliness:
  standard_params_only: true/false
  extra_params: []  # 技术债务列表
```

## 3.2 补丁"三可"原则

所有源码修改必须以 `.patch` 文件保存（由 `refresh-patch.sh --auto` 生成），满足：

- **可复现**：原始 tarball + 补丁集 → 100% 重现相同产物
- **可验证**：`patch --dry-run -p1` 干净通过
- **可上游**：逻辑清晰、有 `#ifdef __OHOS__` 守卫、可提交给上游

**禁止**：sed 直接改 configure/Makefile 等生成文件（不可复现）。修改层级优先级：① configure.ac/CMakeLists.txt/源码 > ② configure/Makefile.in > ③ Makefile > ④ 禁止改二进制。

## 3.3 危险库静态编译要求

以下库**必须静态编译**（LD_LIBRARY_PATH 陷阱会导致系统工具崩溃）：

| 库 | 等级 | 编译要求 |
|---|------|---------|
| ncurses | 🔴 致命 | `--without-shared` |
| readline | 🟠 高 | 建议静态 |
| zlib | 🟠 高 | 建议静态 |

详见 `dependencies.md` 完整分级表。

## 3.4 软链接处理（鸿蒙特有）

HMDFS 文件系统限制软链接：
1. 不能仅检查 `-L` 存在性，必须验证可执行
2. 禁止 `ln -sf` 覆盖（会产生随机后缀文件）
3. 必须用 `rm -f` + `ln -s`
4. 不可用时用 wrapper 脚本替代

详见 `environment.md` 第 9 节。

---

# 四、工具参考表

## 4.1 脚本调用关系图

```
                    ┌─────────────────────┐
                    │   用户/AI 入口       │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │init-build│  │--resume  │  │search-url│
     │   .sh    │  │          │  │   .sh    │
     └────┬─────┘  └──────────┘  └──────────┘
          │
    ┌─────┼───────────────┬──────────────┐
    ▼     ▼               ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│registry│  │init-archive│  │check-env │  │auto_discover│
│_append │  │   .sh    │  │   .sh    │  │registry_append│
└────────┘  └──────────┘  └──────────┘  └──────────────┘
                                           
                    (Step 1 完成: .build-context 就绪)
                    
                           │
                    ▼ Step 2: AI 编译
                  ┌─────────────┐
                  │  Phase 3     │
                  │ (AI 决策)    │
                  └──────┬──────┘
                         │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │detect-bld│  │verify-sym│  │sign-elf  │
     │  sys .sh │  │  links.sh│  │   .sh    │
     └──────────┘  └──────────┘  └──────────┘
                         │
                    ▼ Step 3: finish
              ┌─────────────────────┐
              │  finish-build.sh    │
              └──┬──────────┬───────┬┘
                 │          │       │
         ┌──────▼───┐ ┌───▼───┐ ┌──▼──────┐
         │refresh-  │ │close-  │ │verify-  │ ← 新增: 自动调用
         │patch.sh  │ │archive│ │build.sh │   质量门禁 G1-G4
         │ --auto   │ │  .sh   │ │         │
         └────┬─────┘ └───┬───┘ └────┬────┘
              │           │          │
              ▼           ▼          ▼
         (补丁完成)   (归档关闭)  (门禁报告)
                                │
                    ┌───────────▼───────────┐
                    │ finalize-archive.sh    │  ← Step 4 (原 Step 3)
                    │ gen_summary.py         │  ← Step 5 (原 Step 4)
                    └────────────────────────┘

                           │
                    ▼ Step 4: 质量门禁复查（可选）
              ┌─────────────────────┐
              │  verify-build.sh     │  ← 仅单独复查时手动执行
              │  G1:二进制 G2:功能    │
              │  G3:可移植 G4:档案    │
              └──────────┬──────────┘
                         │
                 ▼ PASS/FAIL
              ┌─────────────────────┐
              │ quality-report.md    │
              └─────────────────────┘
```

## 4.2 工具一览

| 脚本 | 用途 | 调用时机 | 层级 |
|------|------|---------|------|
| `init-build.sh` | 编译初始化（下载/解压/检索/骨架/环境/上下文） | Step 1 | Layer2 |
| `finish-build.sh` | **编译收尾**（补丁+归档+**质量门禁**+校验+总结） | Step 3 | Layer1 |
| `refresh-patch.sh --auto` | 补丁管线（diff/拆分/校验/验证/hash） | finish 内部 | Layer1 |
| `search-download-url.sh` | URL 搜索（5 种策略） | init 内部 fallback | Layer3 |
| `init-archive.sh` | 档架骨架创建 | init 内部 | Layer1 |
| `check-env.sh` | 环境变量检查 | init 内部 | Layer1 |
| `detect-build-system.sh` | 构建系统检测 | Step 2 可选 | Layer1 |
| `verify-symlinks.sh` | 软链接验证 | Step 2 安装后 | Layer1 |
| `sign-elf.sh` | ELF 签名四步流程 | 打包时 | Layer1 |
| `check-knowledge-gap.sh` | 知识提取遗漏检查 | finish 后可选 | Layer1 |
| `verify-build.sh` | **产物质量门禁**：4道检测(二进制/功能/可移植/档案) | **finish-build.sh Step 3（自动）/ Step 4（复查）** | Layer1 |
| `finalize-archive.sh` | **归档收口**：清理+校验+一致性检查 | **Step 5.5（必须）** | Layer1 |
| `close-archive.sh` | 归档收尾 | finish 内部 | Layer1 |
| `software-registry.yaml` | 软件元数据缓存（自动增长） | init 读取/写入 | 数据 |

---

# 五、知识检索路径与知识库价值

> **核心原则：知识库是 SKILL 最有价值的资产，值得消耗上下文来积累和维护。**
> 每个 error-patterns.md 条目 = 节省未来 10-30 分钟的调试时间。
> 每次 Phase 3 遇到的新问题 -> 立即判断是否通用 -> 是则写入 knowledge/ -> 下次直接命中。

## 5.1 检索路径

| 需要找什么 | 去哪找 | 价值 |
|-----------|--------|------|
| 某软件的历史编译方案 | `archives/{首字母}/{软件名}/{版本}/` | 复用完整方案（补丁+配置） |
| **某类错误的通用解法** | **`knowledge/error-patterns.md`（按 E 编号查找）** | **最高价值——避免重复踩坑** |
| 构建系统适配策略 | `knowledge/build-systems.md` | config.guess/sub/修改层级 |
| 平台限制（musl/SELinux/签名） | `knowledge/environment.md` + `harmonyos-specifics.md` | 平台真理 L1 |
| **依赖编译顺序** | **`dependencies.md` + `PREBUILD_TODOLIST.md`** | **防止顺序错误导致连锁失败** |
| 打包/RPATH/签名 | `knowledge/packaging.md` | 可移植性保证 |
| 所有软件兼容性总览 | `SUMMARY.md`（自动生成） | 全局视图 |

## 5.2 知识库增长曲线

```
第 1 个软件: error-patterns.md 有 ~20 条（基础平台问题）
第 5 个软件: error-patterns.md 有 ~40 条（常见构建模式）
第 10 个软件: error-patterns.md 有 ~60 条（大部分错误已覆盖）
第 20 个软件: 新错误 80%+ 已在库中 → 编译时间从 2h 缩减到 30min
第 29 个软件: 接近"一键编译"体验
```

## 5.3 知识积累的 ROI

| 投入 | 回报 |
|------|------|
| 写一条 E-编号错误模式（~5min） | 未来每次遇到同类问题节省 10-30min |
| 记录一个 configure.ac 补丁模板 | 同构建系统的所有后续软件复用 |
| 更新 dependencies.md 危险表 | 所有依赖该库的软件受益 |
| 完善 build-systems.md 决策树 | AI 不再纠结"改哪层" |

# 六、附录

## 6.1 标准归档目录结构（⭐ 强制规范）

> **每个归档必须包含以下文件。** init-archive.sh 创建骨架时应生成全部必填文件。

```
archives/{首字母}/{软件名}/                    ← 软件级（跨版本）
│
├── README.md              # ⭐ 必填：编译说明 + 平台适配要点（版本级）
├── RELEASENOTE.md         # ⭐ 必填：发布说明（软件级，聚合多版本）
├── install.sh            # ⭐ 必填：安装脚本（软件级，参数化: sh -s -- <ver>）
│
└── {版本}/               ← 版本级（每次编译的快照）
    ├── manifest.yaml      # ⭐ 必填：元数据
    ├── PROGRESS.md        # ⭐ 必填：编译进展记录
    │
    ├── patches/           # ⭐ 必填：补丁目录
    │   ├── 0001-{file}.patch
    │   └── ...
    │
    ├── reports/           # ⭐ 必填：报告目录
    │   ├── test-report.md
    │   ├── skill-feedback.md
    │   └── quality-report.md
    │
    └── packaging/         # 🟡 预编译包（verify PASS 后必须）
        ├── {name}-{ver}-ohos-aarch64.tar.gz
        └── {name}-{ver}-ohos-aarch64-debug.tar.gz
```

#### 必填文件内容规范

| 文件 | 最小内容要求 | 模板/参考 |
|------|-------------|----------|
| **manifest.yaml** | §6.2 全部字段 | init-archive.sh 自动生成 |
| **README.md** | 软件简介 + 构建命令 + 补丁清单 + 已知限制 + 验证方法 | 见下方模板 |
| **PROGRESS.md** | 各 Phase 状态(checkbox) + configure 参数 + 编译结果 + 源码修改清单表 | 见下方模板 |
| **test-report.md** | 测试套件类型 + 通过/失败数 + 失败原因分析(平台限制 vs 真bug) | 无固定模板 |
| **skill-feedback.md** | F编号列表(流程缺失/矛盾/脚本问题) + 严重度 + 建议 | §6.6 格式 |

#### PROGRESS.md 最小模板

> 📌 **权威模板源**: `templates/PROGRESS.md`。init-archive.sh 和此处定义均引用同一文件。修改模板时只需更新该文件即可全局生效。

```markdown
# {软件名} {版本} — 编译进度

> 档案创建时间: YYYY-MM-DD HH:MM:SS
> 最后更新: YYYY-MM-DD (当前状态)
> 当前会话 ID: (可选，用于多轮对话追踪)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ... |
| 版本 | ... |
| 状态 | 🔵 进行中 / ✅ success / ⚠️ partial / ❌ failed |
| 构建系统 | autotools/cmake/meson/... |
| 源码路径 | URL |

## 二、编译阶段（checkbox 实时更新）

### Phase 1: 环境准备
- [ ] init-build.sh 完成 / 源码下载解压

### Phase 2: 编译（configure + make + make install）
- [ ] configure 完成（记录参数和耗时）
- [ ] make 编译完成（记录错误和修复）
- [ ] make install 完成

### Phase 2.5: 独立目录安装验证（⭐ 必须做）
- [ ] 干净源码 + 补丁应用
- [ ] 独立 TEST_PREFIX configure + make install
- [ ] 功能回归测试结果

### Phase 3: 测试验证
- [ ] make check / make test 结果
- [ ] 安全弹窗触发确认

### Phase 4: 预编译包制作（⭐ verify PASS 后必须）
- [ ] Step 1-10 打包流程（见 packaging.md）

### Phase 5: 归档收尾
- [ ] 补丁生成（refresh-patch.sh --auto）
- [ ] manifest.yaml / README.md / PROGRESS.md 更新
- [ ] verify-build.sh 质量门禁

## 三、对话记录（⭐ 断点续传核心）

> **每轮对话结束时必须更新此节。新 AI 会从这里恢复上下文。**

### 对话 #N — YYYY-MM-DD HH:MM
**操作**: （做了什么，如"执行 configure"、"修复 xxx bug"、"制作预编译包"）
**结果**: （成功/失败/部分成功，附关键输出摘要）
**发现的问题**: （遇到的坑、错误信息、根因分析）
**当前状态**: （精确到哪个步骤，下一步该做什么）
**遗留问题**: （未解决的、需要下轮继续的）

---

### 对话 #1 — 2026-04-07 14:00
**操作**: 执行 ./configure --prefix=$DEFAULT_PREFIX
**结果**: ✅ 成功（~310秒），零额外参数
**发现的问题**: 无
**当前状态**: Phase 2 configure 完成，下一步执行 make
**遗留问题**: 无

### 对话 #2 — 2026-04-07 14:30
**操作**: make -j1 && make install
**结果**: ✅ 成功，二进制已安装到 $DEFAULT_PREFIX/bin/sed
**发现的问题**: 无
**当前状态**: Phase 2 完成，下一步进入 Phase 2.5 独立测试
**遗留问题**: 无

（后续每轮对话追加...）

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| ... | ... | ... | ... |

## 五、预编译包交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ... | ... | ... |

## 六、结束记录
- **最终状态**: ...
- **结束时间**: ...
```

#### 文件命名统一

| 用途 | 正确名称 | 禁止名称 |
|------|---------|---------|
| 测试报告 | `test-report.md` | `TEST_REPORT.md` `build-report.md` |
| 质量报告 | `quality-report.md` | （verify-build.sh 固定输出） |
| SKILL 反馈 | `skill-feedback.md` | `feedback.md` |
| 进展记录 | `PROGRESS.md` | `progress.md` `STATUS.md` |

## 6.2 manifest.yaml 必填字段

| 字段 | 说明 |
|------|------|
| software, version, status | 名称/版本/ success\|partial\|failed |
| build_system | autotools\|cmake\|meson\|makefile\|custom-perl |
| compile_date | YYYY-MM-DD |
| dependencies | required + optional 列表 |
| build_config | target/options |
| patches_applied | file + purpose（refresh-patch 自动填充） |
| patch_generation | hash 绑定（refresh-patch 自动填充） |
| build_cleanliness | standard_params_only + extra_params（P0 记录） |
| compatibility | level + issues + notes |
| test_results | type + passed + failed + note |
| knowledge_gained | 本次沉淀（L3 笔记） |

## 6.3 补丁命名规范

- 格式：`NNNN-{文件名}.patch`（四位序号 + 文件名）
- 例：`0001-config.sub.patch`、`0003-configure.patch`
- 内嵌依赖加前缀：`0004-glib-config.guess.patch`

## 6.4 知识分层

| 层 | 归属 | 特征 | 写入时机 |
|----|------|------|---------|
| L1 平台真理 | `knowledge/*.md` | 任何软件都可能遇到 | Phase 3 实时 |
| L2 模式经验 | `knowledge/*.md` 章节 | 同类构建系统复现 | Phase 3 实时 |
| L3 本版笔记 | `manifest.yaml` knowledge_gained | 仅本软件本版本 | Phase 3+4 |

不确定时先标 `⏳ 待评估`，Phase 4 再决定。

## 6.5 PREBUILD_TODOLIST 依赖顺序

编译多款软件时，按此顺序执行（下层依赖上层）：

```
第零阶段: pkg-config
第一阶段: sed → coreutils → gawk          (无外部依赖)
第二阶段: automake → libtool             (Autotools 链)
第三阶段-A: zlib → bzip2 → xz → gzip    (压缩库)
第三阶段-B: openssl → ncurses → libffi   (SSL/终端)
第三阶段-C: gdbm → readline             (数据库/编辑)
第四阶段: wget → rsync → jq → file → tar → dos2unix  (网络/文件)
第五阶段: bash → htop → strace → patch   (高级工具)
第六阶段: texinfo → help2man → libpipeline  (文档/辅助)
第七阶段: man-db                          (文档系统)
```

> **注意**：使用 `init-build.sh` 时无需手动关注此顺序——单个软件的依赖在 registry 的 `known_issues` 中标注。批量编译时参考此顺序。

## 6.6 流程自省（简化版）

编译过程中发现 SKILL 自身问题时，记录到 `reports/skill-feedback.md`：

```markdown
### F{NNN}: {简短描述}
- 类别: 流程缺失 / 矛盾 / 脚本问题 / 导航错误
- 严重: 🔴🟡🟢
- 场景: {在哪步发现的}
- 建议: {怎么改}
```

Phase 4 归档时汇总 feedback 到 manifest.yaml `skill_feedback` 字段。

---

*SKILL.md v4.1 — 最后更新: 2026-04-08*
*v4.1 更新：*
*  - **#3 修复**: finish-build.sh 新增 Step 3 自动调用 verify-build.sh（质量门禁不再遗漏）*
*  - **#7 修复**: 统一状态值体系为 success/partial/failed（清除 pass/fail/completed/closed/tested 幽灵状态）*
*  - §1.3 决策树新增：编译后状态判定分支 + 质量门禁结果处理*
*  - finish-build.sh 3 步 → 5 步（补丁→归档→**验证**→校验→总结）*
*  - verify-build.sh 支持 --software/--version/--archive-dir 参数（可被 finish-build 调用）*
*  - 新增状态转换规则表（verify 通过/失败时的自动升降级逻辑）*
*v4.0 更新：*
*  - 四步走 → 五步走（新增 Phase 2.5 独立目录安装验证 + Step 5 预编译包）*
*  - 九条铁律 → 十条铁律（+R10: $TMPDIR 强制规则）*
*  - 新增 §1.2 AI 执行风格规范（shell 脚本原则 / configure 耗时参考）*
*  - 新增 §2.2.1 make check / make test 标准步骤*
*  - 新增 §1.4/Step 5 预编译包三级触发条件*
*  - §6.1 归档目录结构标准化（必填文件清单 + 命名统一 + README/PROGRESS 模板）*
*设计原则：精准（五步走）| 可复现（独立测试保证）| 可分发（预编译包标准）| 可信赖（质量门禁 + 测试套件）*
�档/辅助)
第七阶段: man-db                          (文档系统)
```

> **注意**：使用 `init-build.sh` 时无需手动关注此顺序——单个软件的依赖在 registry 的 `known_issues` 中标注。批量编译时参考此顺序。

## 6.6 流程自省（简化版）

编译过程中发现 SKILL 自身问题时，记录到 `reports/skill-feedback.md`：

```markdown
### F{NNN}: {简短描述}
- 类别: 流程缺失 / 矛盾 / 脚本问题 / 导航错误
- 严重: 🔴🟡🟢
- 场景: {在哪步发现的}
- 建议: {怎么改}
```

Phase 4 归档时汇总 feedback 到 manifest.yaml `skill_feedback` 字段。

---

*SKILL.md v4.0 — 最后更新: 2026-04-07*
*v4.0 更新：*
*  - 四步走 → 五步走（新增 Phase 2.5 独立目录安装验证 + Step 5 预编译包）*
*  - 九条铁律 → 十条铁律（+R10: $TMPDIR 强制规则）*
*  - 新增 §1.2 AI 执行风格规范（shell 脚本原则 / configure 耗时参考）*
*  - 新增 §2.2.1 make check / make test 标准步骤*
*  - 新增 §1.4/Step 5 预编译包三级触发条件*
*  - §6.1 归档目录结构标准化（必填文件清单 + 命名统一 + README/PROGRESS 模板）*
*设计原则：精准（五步走）| 可复现（独立测试保证）| 可分发（预编译包标准）| 可信赖（质量门禁 + 测试套件）*
