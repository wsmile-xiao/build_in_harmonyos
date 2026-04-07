---
name: openharmony-compile-agent
description: 鸿蒙系统编译智能体——三方库预编译框架
version: 3.0.0
author: OpenHarmony PC Developer社区
permissions: 文件读写权限、Shell执行权限、网络访问权限
---

> **每次编译任务前先读本文档。** 本文档回答"怎么做"，KNOW_YOUR_WHY.md 回答"为什么"。

---

# 一、快速参考卡（AI 先看这里）

## 1.1 标准工作流：四条命令

```bash
# ═══ Step 1: 初始化（全自动，~30秒）═══
./scripts/init-build.sh <软件名> [<版本>] [--url=URL]
#   输出: .build-context-<name>-<ver>
#   完成: 下载/解压/检索历史/创建骨架/环境检查

# ═══ Step 2: 编译（唯一需要 AI 的步骤）═══
source .build-context-<name>-<ver>   # 加载上下文变量
cd $BUILD_SRC_DIR                   # 进入源码目录
./configure --prefix=$DEFAULT_PREFIX && make && make install
#   记录修改意图到 PROGRESS.md
#   触发安全弹窗确认

# ═══ Step 3: 收尾（全自动，~10秒）═══
./scripts/finish-build.sh <软件名> <版本> success|partial|failed
#   完成: 补丁生成+归档+总结报告

# ═══ Step 4: 质量门禁（全自动，~15秒）═══  ← 编译成功 != 产物可用！
./scripts/verify-build.sh <软件名> <版本>
#   4 道门禁: 二进制完整性 → 功能可用性 → 可移植性 → 档案完整性
#   输出: reports/quality-report.md + PASS/FAIL 判定
#   FAIL 则不能标记为 success，只能 partial 或 failed
```

**特殊情况**：
```bash
# 新软件（registry 无记录）→ 自动搜索 URL 或手动指定
./scripts/init-build.sh libnew 1.0 --url=https://...

# 会话中断后恢复
./scripts/init-build.sh --resume

# 只做补丁不重新编译
./scripts/refresh-patch.sh --auto <软件名> <版本>
```

## 1.2 九条铁律（违反任何一条都是 bug）

| # | 规则 | 正确做法 | 禁止 |
|---|------|---------|------|
| R1 | **参数最少化** | `./configure --prefix=$P && make` | 加 `--build/--host`/CFLAGS hack |
| R2 | **Phase 3 不生成 .patch** | 只改源码+记录到 PROGRESS.md | diff/sed 结果写文件 |
| R3 | **补丁只用 refresh-patch.sh** | `refresh-patch.sh --auto` | 手动 diff/AI 写 patch |
| R4 | **危险库必须静态编译** | ncurses `--without-shared` | 编译共享库导致系统崩溃 |
| R5 | **软链接必须验证可执行 + 禁止 ln -sf** | `verify-symlinks.sh` + `rm -f && ln -s` | 只检查 `-L` 存在性 / `ln -sf` 覆盖 |
| R6 | **禁止修改生成文件** | 只改 configure.ac/CMakeLists.txt/*.c/*.h（源码层） | sed 改 configure/Makefile/Makefile.in（不可复现） |
| R7 | **安全弹窗必须先触发再测试** | make install 后 `find $PREFIX/bin -exec {} --version \;` 扫一遍 | 直接跑 make check 不触发弹窗→进程被杀→假阴性 |
| R8 | **源码修改"四不"准则** | `#ifdef __OHOS__` 守卫 / 保持上游风格 / 追加平台分支 | 删跨平台代码 / 硬编码路径 / 改原逻辑流 / 偏离代码风格 |
| R9 | **质量门禁 FAIL 禁止标 success** | verify-build.sh 非零 → partial 或 failed | 产物有问题仍标记成功分发 |

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
```

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

## Step 3: finish-build.sh — Phase 4 全自动

> **编译成功后一条命令完成所有收尾工作。**

```bash
./scripts/finish-build.sh <软件名> <版本> success|partial|failed
```

### 内部执行的 3 个步骤

| 步骤 | 脚本 | 内容 | 失败处理 |
|------|------|------|---------|
| [1/3] | refresh-patch.sh --auto | 从原始 tarball diff → per-file 补丁 → 格式校验 → dry-run → hash 绑定 → 写入 manifest | 失败跳过，继续归档 |
| [2/3] | close-archive.sh | 更新 status → 关闭 PROGRESS.md → 检查知识条目 | 失败则退出(2) |
| [3/3] | gen_summary.py | 重新生成 SUMMARY.md | 失败非致命 |

### 状态选择指南

| 状态 | 使用场景 |
|------|---------|
| `success` | 编译成功 + 测试通过 + 补丁完整 |
| `partial` | 编译成功但部分功能不可用（如 coreutils 只有部分命令可用） |
| `failed` | 编译失败且无法绕过（记录失败原因供后续参考） |

## Step 4: verify-build.sh — 质量门禁（必须）

> **编译成功 ≠ 产物可用。** 这是交付前的最后一道关卡。

```bash
./scripts/verify-build.sh <软件名> <版本>
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

### 可选：制作预编译分发包

如果需要分发（列入 PREBUILD_TODOLIST 或用户要求），在 finish-build 之后执行 10 步打包流程：

详见 `knowledge/packaging.md`（RPATH → Strip → 签名 → 权限 → activate.sh → tar.gz）。

---

# 三、核心规范

## 3.1 P0 参数最少化原则

**目标命令**：`./configure --prefix=$PREFIX && make && make install`（零额外参数）

超出 `--prefix` 和软件自身选项的参数 = 技术债务。

| 参数类型 | 是否应该存在 | 消除方法 |
|---------|-------------|---------|
| `--prefix=$PREFIX` | ✅ 必须 | — |
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
              └──┬──────────┬───────┘
                 ▼          ▼
         ┌──────────┐ ┌──────────┐
         │refresh-  │ │close-    │
         │patch.sh  │ │archive.sh│
         │ --auto   │ │          │
         └────┬─────┘ └────┬─────┘
              ▼           ▼
         ┌──────────┐ ┌──────────┐
         │gen_summary│ │manifest  │
         │   .py    │ │ .yaml    │
         │          │ │ (自动更新)│
         └──────────┘ └──────────┘

                           │
                    ▼ Step 4: 质量门禁（必须）
              ┌─────────────────────┐
              │  verify-build.sh     │
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
| `finish-build.sh` | 编译收尾（补丁+归档+总结） | Step 3 | Layer1 |
| `refresh-patch.sh --auto` | 补丁管线（diff/拆分/校验/验证/hash） | finish 内部 | Layer1 |
| `search-download-url.sh` | URL 搜索（5 种策略） | init 内部 fallback | Layer3 |
| `init-archive.sh` | 档架骨架创建 | init 内部 | Layer1 |
| `check-env.sh` | 环境变量检查 | init 内部 | Layer1 |
| `detect-build-system.sh` | 构建系统检测 | Step 2 可选 | Layer1 |
| `verify-symlinks.sh` | 软链接验证 | Step 2 安装后 | Layer1 |
| `sign-elf.sh` | ELF 签名四步流程 | 打包时 | Layer1 |
| `check-knowledge-gap.sh` | 知识提取遗漏检查 | finish 后可选 | Layer1 |
| `verify-build.sh` | **产物质量门禁**：4道检测(二进制/功能/可移植/档案) | **Step 4（必须）** | Layer1 |
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

## 6.1 档案目录结构

```
archives/{首字母}/{软件名}/{版本}/
├── manifest.yaml        # 元数据（必须）✅ git 追踪
├── README.md            # 编译说明（必须）✅ git 追踪
├── patches/             # 补丁（refresh-patch.sh 自动生成）✅ git 追踪
│   ├── 0001-xxx.patch
│   └── ...
├── reports/
│   ├── skill-feedback.md   # SKILL 流程反馈（每次必填）✅ git 追踪
│   ├── test-report.md      ✅ git 追踪
│   └── compatibility.md    ✅ git 追踪
├── scripts/             # 编译脚本（可选）✅ git 追踪
├── logs/                # 完整日志（可选）
├── *.tar.gz             # ❌ 原始源码包 — .gitignore，不上传
├── bin/ lib/ include/   # ❌ 编译产物 — .gitignore，可从补丁重建
└── share/               # ❌ 同上
```

> **git 追踪原则**：git 只追踪"怎么编译"（补丁 + manifest + 知识库），不追踪"编译结果"（tarball + 二进制）。任何人在任何机器上拿到仓库后，通过 `init-build.sh` 下载源码 + 应用 patches 即可 100% 复现相同产物。

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

*SKILL.md v3.1 — 最后更新: 2026-04-04*
*设计原则：精准（四步走）| 优雅（自动降级）| 可复用（registry 增长）| 可社区（三可补丁）| 可信赖（质量门禁保证产物可用）*
