---
# 固定元数据头（必须，AI 优先读取）
name: openharmony-compile-agent
description: 鸿蒙系统编译智能体，提供软件编译的完整流程指导、知识库检索和档案管理
version: 2.2.0
author: OpenHarmony PC Developer社区
permissions: 文件读写权限、Shell执行权限、网络访问权限（可选，用于下载源码）
---

> **🫀 每次开始编译任务前，先读 `KNOW_YOUR_WHY.md`（~2KB）。每次 Phase 3→4 转换时，再读一遍。**
> 那份文档回答"你为什么存在"和"绝对不能忘什么"。本文档回答"怎么做"。

# OpenHarmony 编译智能体 SKILL

## 1. Description

本技能是一个**智能编译助手**，帮助 AI 高效完成鸿蒙系统上的软件编译任务。核心能力：

1. **编译执行指导**：标准化的编译流程和问题排查
2. **知识库检索**：快速定位历史经验和解决方案
3. **档案管理**：结构化存储补丁、报告和元数据
4. **质量保证**：验证编译结果和兼容性评估

### ⚠️ 强制规范

> **软链接处理**：鸿蒙系统的 SELinux 策略限制软链接。在编译、安装、验证的各个阶段，**必须验证软链接是否可执行**，不能仅检查是否存在。详细规范见 `knowledge/environment.md` 第 9 节。

> **代码来源**：所有源码**必须从官方一手源下载**，不得使用第三方镜像或非官方源。这确保代码与常规理解的功能匹配，避免安全风险。下载前需确认官方发布地址。

> **官方测试**：执行官方测试套件（如 `make check`）是**强制要求**，不是可选项。必须运行测试并记录结果，即使测试因环境限制失败也需明确记录原因。

> **核心功能验证**：编译后**必须验证核心功能**，不能只测试 `--version`。例如：
> - htop：必须测试进程显示、F键功能
> - strace：必须测试实际系统调用追踪
> - rsync：必须测试文件同步功能
> 核心功能异常必须在档案中记录原因和解决方案。

> **依赖软件独立归档**：编译目标软件时，如果需要先编译安装依赖库（如 libpipeline 之于 man-db），这些依赖软件**必须作为独立项目单独创建归档**（manifest.yaml + README.md），不能仅作为主软件归档的一个章节。每个依赖库有自己的版本生命周期和补丁记录，独立归档有助于未来复用和跨项目引用。

> **打包验证完整性**：制作可移植包时，**必须对所有 ELF 文件（包括 lib-dynload/ 下的扩展模块）设置 RPATH 并重新签名**。不能仅处理主程序和主共享库而遗漏扩展模块。详见 `knowledge/packaging.md` §3 和 `knowledge/error-patterns.md` E042。

> **Shell 脚本 POSIX 兼容**：为鸿蒙编写的所有 shell 脚本**必须使用 POSIX 兼容语法**（`#!/bin/sh` + toybox ash 兼容），不能依赖 `${BASH_SOURCE}`、`[[ ]]`、数组等 bash 特性。详见 `knowledge/harmonyos-specifics.md` §3。

## 2. When to use

- 用户说："帮我在鸿蒙电脑上编译 XXX"
- 用户说："XX 软件在鸿蒙上编译失败，如何解决"
- 用户说："查询 XX 软件的编译历史"
- 用户说："生成 XX 软件的兼容性报告"
- 用户说："鸿蒙系统用什么编译器？"
- 用户说："如何在鸿蒙系统上配置 autotools？"

### 2.1 跨 SKILL 协作：Python 三方库适配

当用户咨询的是 **Python 三方库（PyPI 包）** 的鸿蒙适配时，应加载 [ohos-python-release](https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release) 项目的 `feat/pypi-compat-skill` 分支进行分析。两个 SKILL 的职责划分：

| SKILL | 职责范围 | 触发条件 |
|-------|----------|----------|
| **本 SKILL** (build_in_harmonyos) | C/C++ 开源软件的编译适配、补丁开发、归档管理 | 用户需要编译 C/C++ 库，或三方库适配过程中涉及底层 C 库编译 |
| **ohos-python-release** (pypi-compat-skill) | Python 三方库的鸿蒙兼容性分析、纯 Python 适配、wheel 打包 | 用户咨询 PyPI 包在鸿蒙上的兼容性 |

**协作流程**：纯 Python 包由 pypi-compat-skill 独立处理；包含 C/C++ 扩展的三方库，先由 pypi-compat-skill 分析兼容性，需要编译 C 依赖库时转回本 SKILL 处理。

## 3. How to use

### 3.1 编译任务执行流程

当用户请求编译软件时，按以下阶段执行：

#### Phase 0: 源码获取（必须首先执行）

> **⚠️ 规范**：所有源码必须从官方一手源下载。禁止使用第三方镜像或非官方源。

**步骤**：

1. **确定版本**
   - 优先选择最新稳定版（LTS 版本如果有的话）
   - 如果用户指定了版本，使用用户指定的版本
   - 如果历史档案中有版本记录，参考历史档案的选择

2. **确定下载地址**
   - 官方网站 → Release 页面 → 源码 tarball（.tar.gz / .tar.xz）
   - 常见下载源：GNU（ftp.gnu.org）、PyPI（python.org）、软件官网 Download 页面

3. **下载源码**：`mkdir -p ${TMPDIR:-$HOME/tmp}/builds && cd $_ && curl -fSL -o {name}-{version}.tar.gz {download_url}`

4. **完整性校验**：`curl -fSL -o CHECKSUMS {checksum_url} && sha256sum -c CHECKSUMS --ignore-missing 2>/dev/null`

5. **解压源码**：`tar -xf {name}-{version}.tar.gz && cd {name}-{version} && SOURCE_DIR=$(pwd)`

**源码存储规范**：
- 编译目录统一使用 `${TMPDIR:-$HOME/tmp}/builds/`
- 编译完成后不删除源码，归档时记录 `source_dir` 路径
- 如需重新编译，从原始 tarball 重新解压（不用 `make distclean`）

#### Phase 1: 检索历史知识（必须先执行）

1. 精确匹配：`archives/{首字母}/{软件名}/{版本}/manifest.yaml` → 直接复用补丁和脚本
2. 相似版本：`archives/{首字母}/{软件名}/*/manifest.yaml` → 评估补丁可复用性
3. 构建系统知识：`knowledge/build-systems.md` → 适配策略

**检索命令**：`ls archives/{首字母}/{软件名}/*/manifest.yaml` 检查现成档案，`cat archives/{首字母}/{软件名}/{版本}/manifest.yaml` 查看内容。

#### Phase 1.5: 创建骨架与进度文件（必须，会话安全的起点）

> **⚠️ 强制规范**：在检索完历史知识、确定编译方案后，**必须立即**创建档案骨架和进度文件。
> 这是会话中断后的恢复入口——下次会话读取 PROGRESS.md 即可知道当前进度。
> **绝对不能等到 Phase 4 才创建档案目录。**

**使用工具脚本**（推荐）：

```bash
# 一条命令完成 Phase 1.5 的全部工作：
# - 创建目录结构
# - 生成 manifest.yaml（status: compiling）
# - 生成 PROGRESS.md（从模板）
# - 更新 _index.yaml（status: compiling）
./scripts/init-archive.sh <软件名> <版本> [源码URL] [构建系统类型]

# 示例
./scripts/init-archive.sh libcurl 8.7.1 https://curl.se/download/curl-8.7.1.tar.xz autotools
```

**手动执行**（如需自定义）：

   ```bash
   mkdir -p archives/{首字母}/{软件名}/{版本}/{patches,reports,scripts,logs}
   ```
2. **更新 archives/_index.yaml**
   _index.yaml 由 `scripts/init-archive.sh` 自动管理，详见 `knowledge/collaboration.md` §4。

3. **manifest.yaml（骨架）**
   > manifest.yaml 模板见 `templates/manifest.yaml`，Phase 1.5 创建时 status 设为 `compiling`。

3. **PROGRESS.md（进度文件，核心）**
   > PROGRESS.md 模板见 `templates/PROGRESS.md`，创建时必须填充：
   > - 当前状态（阶段 + 更新时间 + 源码路径）
   > - 每个错误条目必须包含"跨软件通用性评估"字段
   > - 源码修改清单（表格：文件 | 修改原因 | 补丁状态）

**关键规则**：
- PROGRESS.md 在 Phase 1.5 创建，之后每个 Phase 子步骤完成后**立即更新**
- 每个"错误"条目**必须**包含"跨软件通用性评估"字段
- "待办"清单跟踪未完成的归档和知识提取任务
- 会话中断后的恢复流程：读取 PROGRESS.md → 从"当前状态"和"待办"处继续

#### Phase 2: 环境准备

1. **检查环境变量（必须）**
   ```bash
   # 使用工具脚本一键检查（推荐）
   ./scripts/check-env.sh
   
   # 或手动检查关键变量
   echo "TMPDIR: ${TMPDIR:?未设置}"
   echo "CC: ${CC:?未设置}"
   echo "CFLAGS: ${CFLAGS:?未设置}"
   echo "DEFAULT_PREFIX: ${DEFAULT_PREFIX:?未设置}"
   ```
   详细配置参考 `knowledge/environment.md` 第 4 节

2. **检查依赖工具和软链接（必须验证软链接可用性）**

   > 软链接处理规范详见 §6.3

3. 准备编译目录结构

#### Phase 3: 编译执行（带实时记录）

1. 识别构建系统类型（参考 `knowledge/build-systems.md`）
   1.5. **错误分类与处理策略**
   
   > 编译过程中遇到的错误按以下分类处理：
   
   | 错误阶段 | 常见原因 | 处理策略 |
   |---------|---------|---------|
   | **configure** | 缺少依赖/工具、平台不识别 | 参考 `knowledge/build-systems.md` 和 `knowledge/error-patterns.md` |
   | **编译** | 缺少头文件、语法不兼容、警告变错误 | 先查 error-patterns.md，再搜索 knowledge/ |
   | **链接** | 缺少库、符号未定义、LDFLAGS 错误 | 用 `llvm-readelf` 分析依赖链 |
   | **安装** | 软链接失败、权限问题 | 用 wrapper 脚本替代软链接，参考 §6.3 |
   
   **configure 失败回退**：先 `make distclean` 清理旧配置，再重新 `./configure`。
   **编译失败增量修复**：修复源码后 `make -j1`；不确定影响范围时 `make clean && make -j1`。

2. 应用补丁（如有历史档案）
3. 执行编译命令
4. **执行 make install 并检查软链接（必须）**

   ```bash
   # 使用工具脚本验证软链接
   ./scripts/verify-symlinks.sh $HOME/usr/local
   ```

5. **更新 PROGRESS.md（每解决一个问题后立即执行）**

   > **⚠️ 强制规范**：每解决一个编译问题后，必须立即将以下信息写入 PROGRESS.md：
   > - 遇到的错误、阶段（configure/compile/link/install）、错误信息
   > - 根因分析、解决方案
   > - 将每个源码修改记录到"源码修改清单"表格
   > - 更新"当前状态"中的阶段和时间

6. **实时知识提取（每解决一个新问题后立即执行）**

   > **⚠️ 这是本 SKILL 最重要的流程改进。解决一个问题后，不要等到 Phase 4，立即做以下判断：**

   ```
   Q1: 此问题是否只与本软件有关？→ 是：只记录 PROGRESS.md
   Q2: 其他软件是否可能遇到同类问题？→ 是：立即更新 knowledge/；不确定：标记"⏳ 待评估"（Phase 4 处理）
   ```

   **分流规则**：

   | 问题类型 | 应更新的 knowledge/ 文件 | 判断标准 |
   |---------|----------------------|---------|
   | 编译/链接/运行时错误模式 | `error-patterns.md` | 任何 autotools/CMake 项目都可能遇到 |
   | 构建系统特殊处理 | `build-systems.md` / `autotools-patterns.md` | config.guess/config.sub 处理 |
   | 鸿蒙系统限制 | `environment.md` / `harmonyos-specifics.md` | musl/SELinux/文件系统层面的限制 |
   | musl 与 glibc 差异 | `musl-compat.md` | 标准库行为差异 |
   | 编译依赖关系 | `dependencies.md` | 依赖库需要特定的编译顺序或配置 |

   知识分层详细原则见 **§3.5 知识分层原则**

#### Phase 4: 验证与归档

1. **验证编译产物（必须检查软链接可用性）**
   ```bash
   # 使用工具脚本验证所有软链接
   ./scripts/verify-symlinks.sh $HOME/usr/local
   ```
   **测试前置准备（鸿蒙特有，必须执行）**：
   
   > **⚠️ 鸿蒙环境下测试前必须完成以下三个前置步骤**，否则测试结果可能大面积误报。
   
   1. **预确认弹窗**：触发所有新编译二进制的首次运行确认，避免 Permission denied 被误判为功能问题
   2. **禁止并行测试**：`export MAKEFLAGS="-j1"`（鸿蒙 FIFO 限制导致并行 jobserver 失效）
   3. **设置超时**：`timeout 1800 make check`（防止某些测试卡住导致会话超时）
   
   **测试失败分类标准**：
   | 失败类型 | 根因 | 处理方式 |
   |---------|------|---------|
   | Permission denied | SELinux / 弹窗未确认 | 非功能问题，记录在 manifest 兼容性中 |
   | Symlink 相关 | HMDFS 限制 | 非功能问题，记录在 manifest 兼容性中 |
   | Assertion / Crash | 真正的代码问题 | 必须修复，生成补丁 |
   | Timeout | FIFO 限制 / 死锁 | 检查是否需要 -j1，记录在 manifest 中 |
   | 未知 | 需要进一步调查 | 运行 verbose 模式获取更多信息 |

2. **执行官方测试套件（必须）**
   - 运行 `make check` 或 `make test`，记录通过/失败/跳过
   - 创建测试报告 `reports/test-report.md`，测试失败须在 manifest.yaml 中说明原因
3. **补丁完整性校验（必须，在生成补丁之前执行）**
   > **⚠️ 强制规范**：生成补丁前必须与原始源码做 diff 比对，确保所有源码修改都被捕获为补丁文件。
   
   1. 从原始 tarball 解压到临时目录
   2. `diff -ruN` 对比修改后源码与原始源码，输出 all_changes.diff
   3. 检查 diff 结果：无差异则跳过；有差异则确认每个修改都有对应补丁文件（排除 build/ 等构建产物）
   4. 使用 `./scripts/refresh-patch.sh` 基于三目录法生成/刷新补丁
   
   **校验要点**：
   - 对话中讨论的补丁数量必须与 diff 结果一致
   - diff 中的每个文件修改都必须有对应的补丁文件
   - 如果发现遗漏的修改，必须补充生成补丁
   - **典型案例**：编译过程中临时修改的源文件容易在归档时被遗漏

4. 完善软件档案：
   - 生成补丁文件（基于上一步的校验结果）
   - 验证每个补丁可干净应用：`patch --dry-run -p1 < patches/NNNN-xxx.patch`
   - **完善** manifest.yaml（Phase 1.5 已创建骨架，此处填充最终数据）
   - 编写 README.md
   - 记录测试报告

5. **更新 SUMMARY.md（必须，归档后立即执行）**
   > **⚠️ 强制规范**：每次新增或更新编译档案后，**必须运行 `gen_summary.py` 重新生成 SUMMARY.md**。

   ```bash
   # 归档收尾（一条命令更新 status 并关闭 PROGRESS.md）
   ./scripts/close-archive.sh <软件名> <版本> success|partial|failed
   
   # 生成 SUMMARY.md
   python3 scripts/gen_summary.py
   ```

6. **知识库校验与补充（必须，Phase 4 最后一步）**
   > **⚠️ 强制规范**：既然实时知识提取已在 Phase 3 Step 6 完成，Phase 4 Step 6 的职责变为**校验与补充**，
   > 不再是从零回忆。这是一道安全网，确保编译过程中忙于调试时没有遗漏知识提取。

   **使用工具脚本**（推荐）：`./scripts/check-knowledge-gap.sh <软件名> <版本>` → 输出待评估条目列表、校验报告。

   **手动校验步骤**：

   1. 读取 PROGRESS.md 中标记为"⏳ 待评估"的条目，逐一评估是否需要写入 knowledge/（参考 §3.5 知识分层原则）
   2. 检查本次编译涉及的 knowledge/ 文件是否已正确更新（`grep "⏳ 待评估" PROGRESS.md`）
   3. 补漏检查——回顾本次编译所有错误，确认"知识库更新"字段非空、"跨软件通用性评估"非"⏳ 待评估"
   4. 如果发现遗漏，立即补充更新：分配编号、补充内容、更新索引；将 L3 知识写入 manifest.yaml 的 knowledge_gained

   > **设计意图**：Phase 4 Step 6 是知识提取的"安全网"（主流程在 Phase 3 Step 6），确保编译过程中忙于调试跳过的实时提取不会遗漏知识。

### 3.2 知识检索策略

| 检索场景 | 检索路径 | 用途 |
|----------|----------|------|
| 精确软件版本 | `archives/{letter}/{name}/{version}/` | 复用完整方案 |
| 相似版本 | `archives/{letter}/{name}/` | 评估补丁兼容性 |
| 构建系统知识 | `knowledge/build-systems.md` | 适配策略 |
| 环境配置 | `knowledge/environment.md` | 系统特性 |
| 调试方法论 | `knowledge/debug-methodology.md` | 错误分类→根因路径→降级策略 |
| 依赖递归处理 | `knowledge/dependency-resolution.md` | 检测/判断/隔离环境/循环依赖 |
| 协作规范 | `knowledge/collaboration.md` | 分支策略/PR 规范/主编审核/冲突解决 |
| 鸿蒙特有机制 | `knowledge/harmonyos-specifics.md` | 签名、SELinux、安全模型 |
| __OHOS__/平台适配 | `knowledge/ohos-adaptation-patterns.md` / `knowledge/platform-adaptation-scan.md` | 适配模式/遗漏扫描 |
| 可移植打包/发布 | `knowledge/packaging.md` / `knowledge/release.md` | RPATH/strip/签名/install |
| Python 扩展编译 | `knowledge/python-extensions.md` | musl BIND_NOW、静态链接 |
| ptrace 替代/sudo/文件系统 | `knowledge/ptrace-alternatives.md` / `knowledge/sudo-analysis.md` / `knowledge/filesystem-analysis.md` | 替代方案/差异/架构 |
| 常见问题 | `knowledge/FAQ.md` | 常见问题快速查询 |
| 常见问题 | `knowledge/troubleshooting.md` | 问题排查 |
| 错误模式 | `knowledge/error-patterns.md` | 解决方案 |
| 兼容性总览（人可读） | `SUMMARY.md` | 所有软件的兼容性一览和详情链接 |

### 3.3 软件档案结构

每个成功编译的软件应创建标准化档案：

```
archives/{首字母}/{软件名}/{版本}/
├── manifest.yaml        # 元数据清单（必须）
├── README.md            # 编译说明（必须）
├── patches/             # 补丁目录
│   ├── 0001-xxx.patch
│   └── 0002-xxx.patch
├── reports/             # 报告目录
│   ├── build-report.md  # 编译过程记录
│   ├── test-report.md   # 测试报告
│   └── compatibility.md # 兼容性评估
├── scripts/             # 编译脚本（可选）
│   └── build.sh
└── logs/                # 完整日志（可选）
    └── build.log
```

### 3.4 manifest.yaml 规范

完整示例见 `templates/manifest.yaml`。必须字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| software, version, status | 必须 | 软件名、版本号、编译状态(success/partial/failed) |
| build_system | 必须 | autotools/cmake/meson/makefile/custom-perl |
| compile_date | 必须 | 编译日期 YYYY-MM-DD |
| dependencies | 必须 | required/optional 依赖列表 |
| build_config | 必须 | 编译配置（target、options） |
| patches_applied | 可选 | 已应用补丁列表（file + purpose） |
| compatibility | 必须 | level(high/medium/low) + issues + notes |
| test_results | 必须 | type(official/manual/skipped) + passed + failed + note |
| knowledge_gained | 可选 | 本次编译的知识沉淀 |

### 3.5 知识分层原则

知识分为三层，各层有明确的归属和写入时机：

| 层级 | 名称 | 归属 | 特征 | 写入时机 |
|------|------|------|------|---------|
| L1 | 平台真理 | `knowledge/*.md` | 从 Linux 移植任何软件到鸿蒙都可能遇到（如 musl、SELinux、/tmp） | Phase 3 Step 6 |
| L2 | 模式经验 | `knowledge/*.md` 特定章节 | 特定条件下复现（如 autotools 项目、Python C 扩展） | Phase 3 Step 6 |
| L3 | 本版本笔记 | `manifest.yaml` knowledge_gained | 仅与本软件本版本相关（如具体配置选项） | Phase 3 实时写入，Phase 4 完善 |

**判断流程**：与本软件本版本强绑定 → L3；与平台机制有关（musl/SELinux/文件系统/内核） → L1；与其他同类软件模式相同 → L2；否则 → L3。

**关键原则**：
- L1 和 L2 写入 `knowledge/`，L3 写入 `manifest.yaml`
- 不确定时先标记为"⏳ 待评估"，Phase 4 Step 6 再处理
- 宁可多写一条 L1/L2，也不要把通用知识降级为 L3

### 3.6 archives/ 与 knowledge/ 的职责边界

**archives/**：同一软件不同版本复用（补丁、配置、测试结果），Phase 1.5 创建骨架，Phase 4 完善归档。
**knowledge/**：任何软件编译时参考（错误模式、平台限制、适配方法论），Phase 3 实时提取，Phase 4 校验补充。

**⚠️ 常见错误**：平台通用知识（如 SELinux 限制软链接）应写入 `knowledge/` 而非仅记录在单软件档案中；软件特定配置（如 configure 选项）不应写入 `knowledge/`。

## 4. Directory Structure

```
build_in_harmonyos/
├── SKILL.md                    # 主流程文档（永久保留）
├── KNOW_YOUR_WHY.md            # 约束、理念、工作流规则（永久保留）
├── README.md                   # 项目说明
├── SUMMARY.md                  # 兼容性总览（由 gen_summary.py 自动生成，不可手动编辑）
├── CHANGELOG.md                # 变更日志
├── CONTRIBUTING.md             # 贡献指南
│
├── knowledge/                  # 跨软件知识库（详见 §3.2 检索策略）
│
├── templates/                  # 模板文件（manifest.yaml, PROGRESS.md, README.md, 报告模板, 安装/卸载/补丁脚本）
│
├── scripts/                    # 辅助脚本（详见 §5 Tools）
│
└── archives/                   # 软件编译档案
    ├── _index.yaml             # 软件索引（快速查找）
    ├── a/                      # 按首字母组织
    ├── b/
    ├── c/
    ├── ...                     # d e f g h j l m n o p r s t w z
    └── _meta/                  # 工作分支元数据（协作用）
```

## 5. Tools

> **工具优先原则**：以下脚本封装了编译流程中的确定性操作。AI 应优先调用脚本，而不是手动执行多步命令——这样既节省 token 又减少出错。

### 5.1 编译流程工具

| 脚本 | 用途 | 使用阶段 |
|------|------|---------|
| `scripts/init-archive.sh` | Phase 1.5 一键创建档案骨架、manifest、PROGRESS.md、更新 _index.yaml | Phase 1.5 |
| `scripts/check-env.sh` | 检查环境变量、编译器、构建工具是否就绪 | Phase 2 |
| `scripts/detect-build-system.sh` | 检测源码的构建系统类型（autotools/cmake/meson/...） | Phase 3 |
| `scripts/verify-symlinks.sh` | 验证安装目录下所有软链接的可用性 | Phase 3 / Phase 4 |
| `scripts/sign-elf.sh` | ELF 签名四步流程（patchelf → 移除签名 → 签名 → chmod） | Phase 3.4 / Phase 4 |
| `scripts/refresh-patch.sh` | 基于三目录法生成/刷新补丁 | Phase 3 / Phase 4 |
| `scripts/check-knowledge-gap.sh` | 检查 PROGRESS.md 中的知识提取遗漏 | Phase 4 Step 6 |
| `scripts/close-archive.sh` | 归档收尾（更新 status、关闭 PROGRESS.md、提示 gen_summary） | Phase 4 |

### 5.2 辅助工具

`scripts/validate-patch.sh`（验证补丁可应用）、`scripts/gen_summary.py`（生成 SUMMARY.md）、`scripts/create-archive.sh`（旧版，推荐 init-archive.sh）、`scripts/generate_manifests.py`（批量生成 manifest）

### 5.3 工具使用示例

```bash
# 完整编译流程工具调用链
./scripts/check-env.sh                              # Phase 2
./scripts/init-archive.sh <name> <ver> <url> <build>  # Phase 1.5
./scripts/detect-build-system.sh ./src/             # Phase 3
# ... 编译 ...
./scripts/verify-symlinks.sh $HOME/usr/local        # Phase 3/4
./scripts/sign-elf.sh --batch $HOME/usr/local       # Phase 4
./scripts/refresh-patch.sh --all orig/ mod/ patches/ # Phase 4
./scripts/check-knowledge-gap.sh <name> <ver>       # Phase 4 Step 6
./scripts/close-archive.sh <name> <ver> success     # Phase 4
python3 scripts/gen_summary.py                      # Phase 4
./scripts/restore-session.sh <name> <ver>           # 恢复上下文
```

## 6. Notes

### 6.1 档案命名规范

- 补丁文件：`NNNN-description.patch`（四位序号 + 描述）
- 报告文件：`{type}-report.md`
- 脚本文件：小写 + 连字符，如 `build.sh`

### 6.2 版本兼容性评估

当检索到相似版本时，评估补丁可复用性：

| 版本差异 | 可复用性 | 说明 |
|----------|----------|------|
| 补丁版本 | 高 | 通常是 bug 修复 |
| 小版本升级 | 中 | API 兼容，可能需要调整 |
| 大版本升级 | 低 | 可能需要重新适配 |

### 6.3 软链接处理规范（强制）

> **⚠️ 强制规范**：鸿蒙系统的 SELinux 策略限制软链接的创建和访问。在编译、安装、验证的各个阶段都必须正确处理软链接问题。

**核心原则**：
1. 不能仅检查软链接是否存在，必须验证是否可执行
2. 禁止使用 `ln -sf` 覆盖已存在的软链接（会创建带随机后缀的文件）
3. 必须使用 `rm -f` + `ln -s` 的方式创建软链接
4. 软链接不可用时必须使用规避方式：wrapper 脚本（推荐）或 cp 复制
5. make install 后必须检查安装产物中的软链接

**详细规范**：参考 `knowledge/environment.md` 第 9 节

## 7. License

本技能遵循 MIT 许可证。 许可证。 MIT 许可证。 许可证。 7. License

本技能遵循 MIT 许可证。 许可证。 MIT 许可证。 许可证。