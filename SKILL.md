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

### 核心设计理念

```
知识不遗漏 → 档案结构化 → 检索高效化 → 复用精准化
```

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

**协作流程**：
```
用户咨询 Python 三方库
    │
    ├─ 纯 Python 包（无 C 扩展）
    │   → pypi-compat-skill 独立处理
    │
    └─ 包含 C/C++ 扩展的三方库
        │
        ├─ pypi-compat-skill 分析兼容性
        │
        └─ 需要编译/适配 C 依赖库
            → 转回本 SKILL 处理 C/C++ 编译
            → 编译完成后将结果返回 pypi-compat-skill
```

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
   - 常见官方下载源：
     - GNU 软件：https://ftp.gnu.org/gnu/{name}/{name}-{version}.tar.gz
     - PyPI（仅 Python）：https://www.python.org/ftp/python/{version}/
     - 其他：查看软件官方网站的 Download 页面

3. **下载源码**
   ```bash
   # 创建编译目录（使用 TMPDIR 避免鸿蒙 /tmp 限制）
   mkdir -p ${TMPDIR:-$HOME/tmp}/builds
   cd ${TMPDIR:-$HOME/tmp}/builds
   
   # 下载（优先用 curl，鸿蒙预装）
   curl -fSL -o {name}-{version}.tar.gz {download_url}
   ```

4. **完整性校验（推荐）**
   ```bash
   # SHA256 校验（如果官方提供了 checksum）
   curl -fSL -o CHECKSUMS {checksum_url}
   sha256sum -c CHECKSUMS --ignore-missing 2>/dev/null || \
     echo "⚠️ 无法校验 SHA256，继续使用下载的文件"
   ```

5. **解压源码**
   ```bash
   tar -xf {name}-{version}.tar.gz
   cd {name}-{version}
   # 记录源码根目录路径，后续 PROGRESS.md 需要用到
   SOURCE_DIR=$(pwd)
   ```

**源码存储规范**：
- 编译目录统一使用 `${TMPDIR:-$HOME/tmp}/builds/`
- 编译完成后不删除源码，归档时记录 `source_dir` 路径
- 如需重新编译，从原始 tarball 重新解压（不用 `make distclean`）

#### Phase 1: 检索历史知识（必须先执行）

```
检索路径：
1. archives/{首字母}/{软件名}/{版本}/manifest.yaml
   → 精确匹配：直接复用补丁和脚本
   
2. archives/{首字母}/{软件名}/*/manifest.yaml
   → 相似版本：评估补丁可复用性
   
3. knowledge/build-systems.md
   → 构建系统知识：适配策略
```

**检索命令示例**：
```bash
# 检查是否有现成档案
ls archives/o/openssl/*/manifest.yaml

# 查看档案内容
cat archives/o/openssl/1.1.1w/manifest.yaml
```

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

1. **档案目录结构**
   ```bash
   mkdir -p archives/{首字母}/{软件名}/{版本}/{patches,reports,scripts,logs}
   ```

2. **更新 archives/_index.yaml（改为自动聚合，见 collaboration.md §4）**
   ```bash
   # 工作分支上：创建 _meta.yaml（不再直接修改 _index.yaml）
   # main 分支合并后：运行 ./scripts/aggregate-index.sh 生成 _index.yaml
   ```
   ```yaml
   - software: {软件名}
     version: {版本号}
     status: compiling          # compiling → success/partial/failed（Phase 4 更新）
     letter: {首字母}
     path: archives/{首字母}/{软件名}/{版本}
   ```

3. **manifest.yaml（骨架）**
   ```yaml
   software: {软件名}
   version: {版本号}
   status: compiling          # compiling → success/partial/failed（Phase 4 更新）
   build_system: unknown      # Phase 3 Step 1 确认后更新
   compile_date: YYYY-MM-DD
   dependencies:
     required: []
     optional: []
   build_config: {}
   patches_applied: []
   compatibility:
     level: unknown
     issues: []
     notes: ""
   test_results:
     type: skipped
     passed: 0
     failed: 0
     note: ""
   knowledge_gained: []
   references: []
   ```

3. **PROGRESS.md（进度文件，核心）**

   ```markdown
   # {软件名} {版本} 编译进度

   ## 当前状态
   - 阶段：Phase 2/3/4
   - 更新时间：YYYY-MM-DD HH:MM
   - 源码路径：/path/to/source

   ## 检索结果
   - 是否有现成档案：有/无/相似版本
   - 复用的补丁/方案：...

   ## 环境准备
   - 依赖工具检查结果
   - 遇到的问题（如有）

   ## 编译过程
   ### 错误 1：{简述}
   - 阶段：configure/compile/link/install
   - 错误信息：...
   - 根因：...
   - 解决方案：...
   - ⚠️ 跨软件通用性评估：✅ 是（其他 X 类软件也会遇到）/ ❌ 否（仅本软件）/ ⏳ 待评估
   - 知识库更新：已更新 knowledge/error-patterns.md E0XX / 未更新（原因）

   ### 错误 2：...

   ## 源码修改清单
   | 文件 | 修改原因 | 补丁状态 |
   |------|---------|---------|
   | src/foo.c | 修复 XXX 编译错误 | ✅ 已生成补丁 0001 / ⏳ 未生成补丁 |

   ## 测试结果
   ...

   ## 待办
   - [ ] 补丁完整性校验（diff 比对）
   - [ ] 知识库更新检查
   - [ ] SUMMARY.md 同步
   ```

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

   > 软链接处理规范详见 §6.4

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
   | **安装** | 软链接失败、权限问题 | 用 wrapper 脚本替代软链接，参考 §6.4 |
   
   **configure 失败回退**：
   ```bash
   # 如果 configure 参数有误，不要直接重跑 configure
   # 必须先清理环境（有些 configure 脚本不会正确覆盖旧配置）
   make distclean 2>/dev/null || rm -rf config.cache config.status
   # 重新配置
   ./configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos \
     --prefix=$DEFAULT_PREFIX {修正后的参数}
   ```
   
   **编译失败增量修复**：
   ```bash
   # 修复源码后，不需要完全重新编译
   make -j1  # 只编译修改过的文件
   # 如果不确定哪些文件受影响
   make clean && make -j1
   ```

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
   解决一个问题后，立即问自己：

   Q1: 这个问题是否只与本软件有关？
       - 是 → 只记录在 PROGRESS.md，不更新 knowledge/
       - 否 → 继续 Q2

   Q2: 其他软件编译时是否可能遇到同类问题？
       - 是 → 立即更新 knowledge/ 文件（见下方分流规则）
       - 不确定 → 在 PROGRESS.md 标记为"⏳ 待评估"，Phase 4 Step 6 再处理
   ```

   **分流规则**：

   | 问题类型 | 应更新的 knowledge/ 文件 | 判断标准 |
   |---------|----------------------|---------|
   | 编译/链接/运行时错误模式 | `error-patterns.md` | 任何 autotools/CMake 项目都可能遇到 |
   | 构建系统特殊处理 | `build-systems.md` / `autotools-patterns.md` | config.guess/config.sub 处理 |
   | 鸿蒙系统限制 | `environment.md` / `harmonyos-specifics.md` | musl/SELinux/文件系统层面的限制 |
   | musl 与 glibc 差异 | `musl-compat.md` | 标准库行为差异 |
   | 编译依赖关系 | `dependencies.md` | 依赖库需要特定的编译顺序或配置 |

   **判断示例**：
   - "musl 的 BIND_NOW 导致 Python 扩展模块加载失败" → ✅ 跨软件通用 → `error-patterns.md` E004
   - "strace 的 m32 personality 检测在纯 aarch64 上失败" → ✅ 跨软件通用 → `build-systems.md` §10.2
   - "ncurses 6.4 的 cchar_t 需要 _XOPEN_SOURCE_EXTENDED" → ✅ 跨软件通用 → `error-patterns.md` E033
   - "OpenSSL 的 RSA-PSS 有 ARM64 汇编 bug" → ❌ 仅 OpenSSL 特有 → 只记录 PROGRESS.md

   知识分层详细原则见 **§3.5 知识分层原则**

#### Phase 4: 验证与归档

1. **验证编译产物（必须检查软链接可用性）**
   ```bash
   # 使用工具脚本验证所有软链接
   ./scripts/verify-symlinks.sh $HOME/usr/local
   
   # 手动验证单个可执行文件
   verify_installation() {
       local bin=$1
       
       # 1. 检查文件存在
       [ -e "$bin" ] || { echo "❌ $bin 不存在"; return 1; }
       
       # 2. 验证可执行性
       "$bin" --version >/dev/null 2>&1 || {
           echo "❌ $bin 无法执行"
           return 1
       }
       
       echo "✅ $bin 验证通过"
       return 0
   }
   ```
   **测试前置准备（鸿蒙特有，必须执行）**：
   
   > **⚠️ 鸿蒙环境下测试前必须完成以下三个前置步骤**，否则测试结果可能大面积误报。
   
   ```bash
   # 1. 预确认弹窗：触发所有新编译的二进制的首次运行确认
   #    跳过此步骤会导致 Permission denied 被误判为功能问题
   find $DEFAULT_PREFIX/bin -type f -executable -exec {} --version \; 2>&1 | head -1
   
   # 2. 禁止并行测试：鸿蒙 FIFO 限制导致并行 jobserver 失效
   export MAKEFLAGS="-j1"
   
   # 3. 设置超时：防止某些测试（如 cat-self.sh）卡住导致会话超时
   timeout 1800 make check
   ```
   
   **测试失败分类标准**：
   | 失败类型 | 根因 | 处理方式 |
   |---------|------|---------|
   | Permission denied | SELinux / 弹窗未确认 | 非功能问题，记录在 manifest 兼容性中 |
   | Symlink 相关 | HMDFS 限制 | 非功能问题，记录在 manifest 兼容性中 |
   | Assertion / Crash | 真正的代码问题 | 必须修复，生成补丁 |
   | Timeout | FIFO 限制 / 死锁 | 检查是否需要 -j1，记录在 manifest 中 |
   | 未知 | 需要进一步调查 | 运行 verbose 模式获取更多信息 |

2. **执行官方测试套件（必须）**
   - 运行 `make check` 或 `make test`
   - 记录测试结果（通过/失败/跳过）
   - 分析失败原因：编译问题 vs 环境兼容性问题
   - 创建测试报告 `reports/test-report.md`
   - 如果测试失败，必须在 manifest.yaml 中说明原因
3. **补丁完整性校验（必须，在生成补丁之前执行）**
   ```bash
   # ⚠️ 强制规范：生成补丁前必须与原始源码做 diff 比对，
   # 确保所有源码修改都被捕获为补丁文件，防止遗漏。
   # 不能仅凭对话记录"回忆"做过哪些修改。
   
   # 1. 从原始 tarball 解压到临时目录
   mkdir -p /tmp/patch_verify
   cd /tmp/patch_verify
   tar xf /path/to/original.tar.xz <软件名>-<版本>/ 2>/dev/null
   
   # 2. 对比修改后的源码与原始源码
   diff -ruN \
       <软件名>-<版本>/ \
       /path/to/modified-source/ \
       > /tmp/patch_verify/all_changes.diff
   
   # 3. 检查 diff 结果
   # - 如果无差异 → 没有源码修改，跳过
   # - 如果有差异 → 逐个检查差异，确认每个修改都已（或将被）生成为补丁文件
   # - 排除 build 目录、.o 文件、Makefile 等构建产物
   ```
   **校验要点**：
   - 对话中讨论的补丁数量必须与 diff 结果一致
   - diff 中的每个文件修改都必须有对应的补丁文件
   - 如果发现遗漏的修改，必须补充生成补丁
   - **典型案例**：编译过程中为修复编译错误临时修改的源文件（如添加 `__attribute__((unused))`），容易在归档时被遗漏
   
   > **教训**：strace 6.19 编译时修改了 `src/sigreturn.c` 抑制 clang 的 `-Wunused-function` 警告，但归档时仅生成了 config.guess 和 config.sub 的补丁，遗漏了源码修改。若当时执行此 diff 校验步骤，即可避免。

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

   **生成内容包含**：
   - 📊 总体统计（软件数量、成功/部分成功/失败分布、构建系统分布）
   - 📋 软件兼容性一览表（状态、兼容性等级、补丁数、依赖、详情链接）
   - 📖 各软件详细信息（兼容性评估、已知问题、补丁列表、报告链接）

6. **知识库校验与补充（必须，Phase 4 最后一步）**
   > **⚠️ 强制规范**：既然实时知识提取已在 Phase 3 Step 6 完成，Phase 4 Step 6 的职责变为**校验与补充**，
   > 不再是从零回忆。这是一道安全网，确保编译过程中忙于调试时没有遗漏知识提取。

   **使用工具脚本**（推荐）：

   ```bash
   # 一键检查知识库遗漏
   ./scripts/check-knowledge-gap.sh <软件名> <版本>
   # 输出：待评估条目列表、缺失的 knowledge_ref、校验报告
   ```

   **手动校验步骤**：

   1. **读取 PROGRESS.md 中标记为"⏳ 待评估"的条目**
      - 逐一评估：这个问题是否需要写入 knowledge/？
      - 参考判断流程（见 §3.5 知识分层原则）

   2. **检查本次编译涉及的 knowledge/ 文件是否已正确更新**
      ```bash
      # 快速检查本次是否遗漏了知识更新
      grep "⏳ 待评估" archives/{首字母}/{软件名}/{版本}/PROGRESS.md

      # 如果有待评估条目，逐一处理
      # 如果没有待评估条目，仍然执行下一步
      ```

   3. **补漏检查——回顾本次编译的所有错误**
      ```
      快速扫描清单：
      - PROGRESS.md "编译过程"中的每个错误条目
        → "知识库更新"字段是否为空？
        → "跨软件通用性评估"是否为"⏳ 待评估"？
      - 是否有新的鸿蒙系统限制被发现但未写入 knowledge/？
      - 本次编译的 L1/L2 知识（见 §3.5）是否已全部写入 knowledge/？
      ```

   4. **如果发现遗漏，立即补充更新**
      - 为新模式分配编号（error-patterns.md 的 E0xx 序号递增）
      - 补充错误特征、根因分析、验证命令、解决方案
      - 更新相关索引表
      - 在 PROGRESS.md 中更新对应条目的"知识库更新"字段

   5. **更新 manifest.yaml 的 knowledge_gained**
      - 将 L3 层知识（仅本版本笔记）写入 manifest.yaml
      - L1/L2 层知识已在 Phase 3 写入 knowledge/，此处不再重复
      - 见 §3.5 知识分层原则

   > **设计意图**：Phase 4 Step 6 是知识提取的"安全网"，不是主流程。
   > 主流程在 Phase 3 Step 6（实时知识提取）。如果 Phase 3 做得充分，
   > Phase 4 Step 6 应该很快就能确认无遗漏。但如果编译过程中忙于调试跳过了实时提取，
   > Phase 4 Step 6 确保知识不会丢失。

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
| 鸿蒙特有机制 | `knowledge/harmonyos-specifics.md` | 签名、SELinux、三层安全模型 |
| __OHOS__ 适配模式 | `knowledge/ohos-adaptation-patterns.md` | 内核 API 复用 vs glibc 特有 |
| 平台适配扫描 | `knowledge/platform-adaptation-scan.md` | 遗漏扫描方法论 |
| 可移植打包 | `knowledge/packaging.md` | RPATH、strip、签名流程 |
| 发布流程 | `knowledge/release.md` | 打包、install/uninstall、GitCode Release |
| Python 扩展编译 | `knowledge/python-extensions.md` | musl BIND_NOW、静态链接、扩展模块 |
| ptrace 替代方案 | `knowledge/ptrace-alternatives.md` | LD_PRELOAD、strace 替代 |
| musl 兼容性 | `knowledge/musl-compat.md` | musl 与 glibc 差异、兼容代码模式 |
| sudo 差异分析 | `knowledge/sudo-analysis.md` | sudo 功能差异、编译场景影响、规避方案 |
| 文件系统分析 | `knowledge/filesystem-analysis.md` | 文件系统架构、挂载点、权限模型 |
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

```yaml
# 必须字段
software: openssl          # 软件名
version: 1.1.1w           # 版本号
status: success           # success | partial | failed
build_system: custom-perl # autotools | cmake | custom-perl | meson | makefile
compile_date: 2024-03-22  # 编译日期

# 依赖信息
dependencies:
  required: [perl]        # 必需依赖
  optional: [zlib]        # 可选依赖

# 编译配置
build_config:
  target: linux-aarch64-ohos
  options:
    - --prefix=$HOME/usr/local
    - no-asm

# 补丁信息
patches_applied:
  - file: 0001-support-build-in-harmonyos.patch
    purpose: 添加 HarmonyOS 平台配置
    lines_changed: 120

# 兼容性评估
compatibility:
  level: high             # high | medium | low
  issues: []              # 已知问题
  notes: "核心功能正常"

# 测试结果
test_results:
  type: manual            # official | manual | skipped
  passed: 29
  failed: 6
  note: "核心加密功能正常"

# 知识沉淀
knowledge_gained:
  - "使用 no-asm 禁用汇编优化避免 BAD_SIGNATURE"
  - "Python _ssl 模块需要手动链接 libssl"

# 参考
references:
  - https://www.openssl.org/docs/
```

### 3.5 知识分层原则

知识分为三层，各层有明确的归属和写入时机：

```
L1: 平台真理（跨所有软件）
   → 归属：knowledge/*.md
   → 特征：如果从 Linux 移植任何软件到鸿蒙都可能遇到
   → 示例：musl 不支持 iconv //IGNORE、SELinux 限制软链接、/tmp 只读
   → 写入时机：解决后立即写入（Phase 3 Step 6）

L2: 模式经验（跨同类软件）
   → 归属：knowledge/*.md 的特定章节
   → 特征：在特定条件下会复现（如 autotools 项目、Python C 扩展）
   → 示例：config.guess 需添加 HarmonyOS 检测、make -j 因 FIFO 限制需改为 -j1
   → 写入时机：解决后立即写入（Phase 3 Step 6）

L3: 本版本笔记（仅此版本）
   → 归属：manifest.yaml 的 knowledge_gained
   → 特征：仅与本软件本版本相关的笔记
   → 示例：OpenSSL 1.1.1w 的具体配置选项、ncurses 6.4 的 --enable-widec
   → 写入时机：Phase 3 实时写入 manifest.yaml 的 knowledge_gained（Phase 4 完善）
```

**判断流程**：

```
解决了一个问题
    │
    ├─ 是否与本软件本版本强绑定？
    │   ├─ 是 → L3（manifest knowledge_gained）
    │   └─ 否 ↓
    │
    ├─ 是否与平台机制有关（musl/SELinux/文件系统/内核）？
    │   ├─ 是 → L1（knowledge/ 对应文件）
    │   └─ 否 ↓
    │
    ├─ 是否与其他同类软件的模式相同？
    │   ├─ 是 → L2（knowledge/ 对应章节）
    │   └─ 否 → L3（manifest knowledge_gained）
```

**关键原则**：
- L1 和 L2 写入 `knowledge/`，L3 写入 `manifest.yaml`
- 不确定时先标记为"⏳ 待评估"，Phase 4 Step 6 再处理
- 宁可多写一条 L1/L2，也不要把通用知识降级为 L3

### 3.6 archives/ 与 knowledge/ 的职责边界

| 维度 | archives/ (档案) | knowledge/ (知识库) |
|------|-----------------|-------------------|
| **目的** | 同一软件不同版本复用 | 任何软件编译时参考 |
| **生命周期** | 跟随软件版本 | 独立于软件版本，长期积累 |
| **检索场景** | "编译 openssl 1.1.1w" → 直接找档案 | "遇到 XXX 错误" → 查 error-patterns.md |
| **内容类型** | 补丁、具体配置、测试结果 | 错误模式、平台限制、适配方法论 |
| **写入时机** | Phase 1.5 创建骨架，Phase 4 完善归档 | Phase 3 实时提取，Phase 4 校验补充 |
| **谁来写** | AI（按 manifest 规范） | AI（按知识分层原则） |

**⚠️ 常见错误**：
- ❌ 把"SELinux 限制软链接"只记录在 openssl 的 README.md → 应同时写入 `knowledge/environment.md`
- ❌ 把"config.guess 需要添加 HarmonyOS 检测"只记录在 strace 的 manifest → 应写入 `knowledge/build-systems.md`
- ❌ 把"本软件的 configure 选项"写入 knowledge/ → 应只记录在 manifest.yaml
- ❌ 把"musl 不支持 XXX 函数"只记录在 PROGRESS.md → 应写入 `knowledge/musl-compat.md`

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
├── knowledge/                  # 跨软件知识库（24 个文件）
│   ├── autotools-patterns.md         # autotools 编译模式
│   ├── best-practices.md             # 编译最佳实践
│   ├── build-systems.md              # 构建系统知识
│   ├── debug-methodology.md          # 调试方法论（错误分类→根因路径→降级策略）
│   ├── dependencies.md               # 编译依赖顺序与推荐顺序
│   ├── dependency-resolution.md      # 依赖递归处理（检测/判断/隔离环境/循环依赖）
│   ├── environment.md                # 鸿蒙环境特性
│   ├── error-patterns.md             # 错误模式库
│   ├── FAQ.md                        # 常见问题
│   ├── filesystem-analysis.md        # 文件系统架构分析
│   ├── filesystem-impact-assessment.md  # 文件系统影响评估
│   ├── harmonyos-specifics.md        # 鸿蒙特有机制（签名、SELinux、安全模型）
│   ├── musl-compat.md                # musl 兼容性
│   ├── musl-glibc-developer-impact.md  # musl/glibc 差异对开发者影响
│   ├── musl-glibc-full-comparison-gnu-linux.md  # musl/glibc 接口对比（GNU+Linux）
│   ├── musl-glibc-full-comparison-iso-posix.md  # musl/glibc 接口对比（ISO C+POSIX）
│   ├── ohos-adaptation-patterns.md   # __OHOS__ 通用适配模式（内核 API vs glibc）
│   ├── packaging.md                  # 可移植打包指南
│   ├── platform-adaptation-scan.md   # 平台适配遗漏扫描方法论
│   ├── ptrace-alternatives.md        # ptrace 替代方案
│   ├── python-extensions.md          # Python 扩展编译
│   ├── release.md                    # 发布流程（打包/install/uninstall/GitCode Release）
│   ├── sudo-analysis.md              # sudo 功能差异分析
│   └── troubleshooting.md            # 问题排查指南
│
├── templates/                  # 模板文件
│   ├── manifest.yaml           # manifest 模板
│   ├── PROGRESS.md             # 编译进度文件模板（Phase 1.5 必须使用）
│   ├── README.md               # README 模板
│   ├── build-report.md         # 编译报告模板
│   ├── compatibility.md        # 兼容性报告模板
│   ├── test-report.md          # 测试报告模板
│   ├── install.sh              # 安装脚本模板（Phase 5 使用）
│   ├── uninstall.sh            # 卸载脚本模板
│   └── apply-patches.sh        # 补丁应用脚本模板
│
├── scripts/                    # 辅助脚本
│   ├── check-env.sh            # 环境检查（Phase 2）
│   ├── check-knowledge-gap.sh  # 知识库遗漏校验（Phase 4 Step 6）
│   ├── close-archive.sh        # 归档收尾/关闭档案（Phase 4）
│   ├── create-archive.sh       # 创建档案（旧版，推荐用 init-archive.sh）
│   ├── detect-build-system.sh  # 构建系统检测
│   ├── gen_summary.py          # 生成 SUMMARY.md
│   ├── generate_manifests.py   # 批量生成 manifest（工具脚本）
│   ├── init-archive.sh         # Phase 1.5 骨架创建（推荐）
│   ├── refresh-patch.sh        # 补丁刷新（三目录法）
│   ├── sign-elf.sh             # ELF 签名四步流程
│   └── validate-patch.sh       # 验证补丁可应用
│
└── archives/                   # 软件编译档案
    ├── _index.yaml             # 软件索引（快速查找）
    ├── a/                      # 按首字母组织
    │   └── automake/
    │       └── 1.16.5/
    ├── b/
    │   ├── bash/
    │   │   └── 5.3/
    │   └── bzip2/
    │       └── 1.0.8/
    ├── c/
    ├── f/
    ├── g/
    ├── h/
    ├── j/
    ├── l/
    ├── m/
    ├── n/
    ├── o/
    ├── p/
    ├── r/
    ├── s/
    ├── t/
    ├── w/
    └── z/
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

| 脚本 | 用途 |
|------|------|
| `scripts/validate-patch.sh` | 验证补丁是否可以干净应用到源码 |
| `scripts/gen_summary.py` | 从档案数据自动生成 SUMMARY.md |
| `scripts/create-archive.sh` | 旧版档案创建（推荐用 init-archive.sh） |
| `scripts/generate_manifests.py` | 批量生成 manifest.yaml |

### 5.3 工具使用示例

```bash
# 完整编译流程中的工具调用链
./scripts/check-env.sh                              # Phase 2: 环境检查
./scripts/init-archive.sh libcurl 8.7.1 ... autotools # Phase 1.5: 创建骨架
./scripts/detect-build-system.sh ./curl-8.7.1        # Phase 3: 识别构建系统
# ... 编译过程 ...
./scripts/verify-symlinks.sh $HOME/usr/local         # Phase 3/4: 验证软链接
./scripts/sign-elf.sh --batch $HOME/usr/local        # Phase 4: 批量签名 ELF
./scripts/refresh-patch.sh --all orig/ modified/ archives/.../patches/  # Phase 4: 生成补丁
./scripts/prep-test.sh $HOME/usr/local               # Phase 4: 测试前置准备
./scripts/check-knowledge-gap.sh libcurl 8.7.1       # Phase 4 Step 6: 知识校验
./scripts/close-archive.sh libcurl 8.7.1 success     # Phase 4: 归档收尾
python3 scripts/gen_summary.py                      # Phase 4: 更新总览

# 上下文压缩后恢复会话
./scripts/restore-session.sh libcurl 8.7.1           # 任意阶段: 恢复上下文
```

### 5.1 档案检索

```

## 6. Notes

### 6.1 知识拆分原则

原有 SKILL.md 内容过大，已拆分为多个知识文件：

| 原位置 | 新位置 |
|--------|--------|
| 构建系统知识 | `knowledge/build-systems.md` |
| 编译依赖顺序 | `knowledge/dependencies.md` |
| 环境检查 | `knowledge/environment.md` |
| 文件系统架构分析 | `knowledge/filesystem-analysis.md` |
| 常见问题 | `knowledge/troubleshooting.md` |
| musl 兼容性 | `knowledge/musl-compat.md` |
| 问题案例 | `knowledge/error-patterns.md` |
| musl/glibc 接口对比 (ISO C + POSIX) | `knowledge/musl-glibc-full-comparison-iso-posix.md` |
| musl/glibc 接口对比 (GNU + Linux) | `knowledge/musl-glibc-full-comparison-gnu-linux.md` |
| musl/glibc 差异对开发者影响 | `knowledge/musl-glibc-developer-impact.md` |
| 可移植打包指南 | `knowledge/packaging.md` |
| 鸿蒙特有机制汇总 | `knowledge/harmonyos-specifics.md` |
| 调试方法论 | `knowledge/debug-methodology.md` |
| 依赖递归处理 | `knowledge/dependency-resolution.md` |
| 发布流程 | `knowledge/release.md` |

### 6.2 档案命名规范

- 补丁文件：`NNNN-description.patch`（四位序号 + 描述）
- 报告文件：`{type}-report.md`
- 脚本文件：小写 + 连字符，如 `build.sh`

### 6.3 版本兼容性评估

当检索到相似版本时，评估补丁可复用性：

| 版本差异 | 可复用性 | 说明 |
|----------|----------|------|
| 补丁版本 | 高 | 通常是 bug 修复 |
| 小版本升级 | 中 | API 兼容，可能需要调整 |
| 大版本升级 | 低 | 可能需要重新适配 |

### 6.4 软链接处理规范（强制）

> **⚠️ 强制规范**：鸿蒙系统的 SELinux 策略限制软链接的创建和访问。在编译、安装、验证的各个阶段都必须正确处理软链接问题。

**核心原则**：
1. **不能仅检查软链接是否存在**，必须验证是否可执行
2. **禁止使用 `ln -sf` 覆盖已存在的软链接**（会创建带随机后缀的文件）
3. **必须使用 `rm -f` + `ln -s` 的方式创建软链接**
4. **软链接不可用时必须使用规避方式**：wrapper 脚本（推荐）或 cp 复制
5. **make install 后必须检查**安装产物中的软链接

**详细规范**：参考 `knowledge/environment.md` 第 9 节

**快速参考**：
```bash
# 创建软链接的正确方式（关键！）
rm -f /path/to/link           # 先删除
ln -s /target /path/to/link   # 再创建（不加 -f）

# 检查软链接
check_symlink "/path/to/link" || create_wrapper "name" "/path/to/target"

# 创建 wrapper 脚本（规避方案）
cat > $HOME/usr/local/bin/cc << 'EOF'
#!/bin/sh
exec /data/service/hnp/bin/clang "$@"
EOF
chmod +x $HOME/usr/local/bin/cc
```

> **关于 clang 路径问题**：鸿蒙的 clang 脚本使用 `exec -a` 设置 argv[0]，所以软链接和 wrapper 脚本都能正确找到 sysroot 和资源目录，不存在路径问题。

## 7. License

本技能遵循 MIT 许可证。 许可证。 MIT 许可证。 许可证。