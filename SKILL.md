---
name: openharmony-compile-agent
description: 鸿蒙系统编译智能体——三方库预编译框架
---

> **每次编译任务前先读本文档。** 骨架 + 要点，详解按需从 references/ 加载。
> KNOW_YOUR_WHY.md 回答"为什么"，本文档回答"怎么做"。

## §0 初始化

```bash
SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
```

> `ohc-run.py` 内部自动定位项目根目录（`find_project_dir()`），不需要手动 `export` 环境变量。
> **R13**: 用完整路径调用，如 `python3 $SKILL_ROOT/scripts/ohc-run.py build ...`。不要用相对路径 `./scripts/xxx`。

### §0.1 协作模式（⭐ 默认生效）

本 skill 默认以**协作者模式**运行，基于 Git + GitCode PR 协作。详见 `knowledge/collaboration.md` 和 `knowledge/collaboration-tutorial.md`。

| 模式 | 触发方式 | 职责 |
|------|---------|------|
| 协作者（默认） | 直接使用 | 编译软件、提取知识、创建分支并提交 PR |
| 主编 | `OHC_ROLE=editor` | 审核 PR、合并知识、重建索引 |

**协作者 Git 铁律（违反=越权）**：
- ❌ 不要直接推送到 main 分支，必须创建功能分支
- ❌ 不要修改 `knowledge/graph/index.tsv`、`archives/_index.yaml`、`SUMMARY.md`
- ❌ 不要修改 `SKILL.md`、`references/`、`templates/`、`scripts/`
- ❌ 不要修改不属于自己负责的软件归档目录
- ✅ 新增知识用 `ohc-run.py graph add E{N} --draft`（写草稿目录）
- ✅ 完成后创建 PR：`git checkout -b feat/{软件名}-{版本}` → commit → push → GitCode PR

**Agent ID**：每个 Agent 实例自动获取 4 位随机标识（如 `A7F3`），用于分支后缀和草稿归属。可通过 `OHC_AGENT_ID` 环境变量预设。

---

## §1 快速参考

### 1.1 两套模式

**模式 A：全自动（推荐，适合大多数三方库）**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> [<版本>]
# → 内含 14 步：init→patches→pre-scan→configure→make→install→staging→package→deploy→finish→...
```
脚本遇到 configure/make 错误时自动输出 HANDOFF 块，AI 修复后 `--resume-from=StepN` 继续。

**模式 B：AI 手动编译（适合复杂/首次编译的软件）**
```bash
# Step 1: 初始化（自动）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL]

# Step 2: 读取上下文，手动编译（唯一需要 AI 的步骤）
# 读取 .build-context-<name>-<ver> 获取 BUILD_SRC_DIR, TEST_PREFIX 等变量
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j$(nproc) && make install DESTDIR=$TEST_PREFIX
make check  # 必须执行，超时可 Ctrl+C 跳过并记录原因

# Step 2.5: 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package <软件名> <版本>

# Step 2.6: 部署到本地 + 用户验证（模拟普通用户部署 install.sh 后的状态）
make install  # 不带 DESTDIR，直接安装到 $DEFAULT_PREFIX（~/usr/local）
$DEFAULT_PREFIX/bin/<软件> --version  # 验证本地安装可用

# Step 3: 收尾（6 步自动）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> success|partial|failed

# Step 4: 质量门禁复查（可选，finish 已自动执行）
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build <软件名> <版本>

# Step 5: 预编译包制作（verify PASS 后必须执行）
# 按 references/packaging-guide.md 10 步流程
```

**如何选择**：已知软件/简单编译 → 模式 A；首次编译/复杂依赖/需深度调试 → 模式 B。

**特殊情况**：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libnew 1.0 --url=https://...    # 新软件
python3 $SKILL_ROOT/scripts/ohc-run.py init-build --resume                          # 恢复中断
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto <软件名> <版本>         # 只做补丁
# 查看所有进行中编译状态（跨对话恢复首选）
python3 $SKILL_ROOT/scripts/ohc-run.py status
# 独立运行知识图谱引擎匹配
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"
```

### 1.2 铁律摘要（23 条，违反=bug）

| # | 规则 | 一句话 | 详解 |
|---|------|--------|------|
| R1 | 参数最少化 | 只需 `--prefix` | references/iron-rules.md |
| R2 | Phase 3 不生成 .patch | 只改源码+记录 PROGRESS | references/patch-pipeline.md |
| R3 | 补丁只用 ohc-run.py refresh-patch | `ohc-run.py refresh-patch --auto` | references/patch-pipeline.md |
| R4 | 危险库静态编译 | ncurses `--without-shared` | §7 Gotchas |
| R5 | 软链接验证可执行+禁止 ln -sf | `rm -f && ln -s` | §7 Gotchas |
| R6 | 只改源文件不改生成文件 | 用 `track-edit` 追踪，refresh-patch 只生成追踪文件的补丁 | references/iron-rules.md |
| R7 | 安全弹窗先触发再测试 | make install 后扫一遍 --version | references/compile-guide.md |
| R8 | 源码"四不"准则 | `#ifdef __OHOS__` 守卫 | references/iron-rules.md |
| R9 | 门禁 FAIL 禁标 success | 降级为 partial/failed | references/iron-rules.md |
| R10 | 临时文件用 $TMPDIR | 禁硬编码 /tmp（只读） | §7 Gotchas |
| R11 | 失败先查归档再动手 | 读 README.md + manifest.yaml | references/failure-handling.md |
| R12 | 先匹配错误模式再修复 | 引擎匹配 graph/index.tsv | references/failure-handling.md |
| R13 | 脚本用完整路径 | `python3 $SKILL_ROOT/scripts/ohc-run.py <cmd>` | §0 |
| R14 | 脚本失败=手动模式入口 | `--resume-from=StepN` 继续 | references/failure-handling.md |
| R15 | 历史仅供参考，不盲从 | 实际参数以本次编译为准，成功后回写 manifest | §4.1 |
| R16 | 协作不越权 | 不推送 main，走 PR 流程 | knowledge/collaboration.md |
| R17 | 知识先草稿 | graph add --draft | knowledge/collaboration.md |
| R18 | 依赖先查预编译 | resolve-deps --install 优先于手动编译 | §1.3 决策树 |
| R19 | 禁止手动打包 | 必须用 ohc-run.py package 10 步管线 | §3 Step 5 |
| R20 | **DESTDIR 模式** | `--prefix=$DEFAULT_PREFIX` + `DESTDIR=$TEST_PREFIX` | §3 Step 2 |
| R21 | **Phase 3 结束必须自检零介入** | 按 §2.4.1 清单逐项检查，所有手动操作已固化 | 不自检就调 finish |
| R22 | **finish 前必须通过干净构建验证** | `ohc-run.py clean-verify` G0 门禁通过 | G0 FAIL 仍标 success |
| R23 | **平台检测机制优先于改生成文件** | 用 hints/config.guess/cmake 检查 | 手动 sed config.sh/config.h |

### 1.3 决策树

```
新三方库？
├─ registry 有记录 → ohc-run.py init-build <name> <ver>           （全自动）
├─ 有 URL → ohc-run.py init-build <name> <ver> --url=URL          （自动注册）
└─ 都没有 → ohc-run.py search-url <name> <ver>           → 从候选选 URL

缺依赖？
├─ 有预编译包 → ohc-run.py resolve-deps --install <name>         （自动安装）
├─ 无预编译包 → 查 dependencies.md 编译顺序 → 先编依赖
└─ 不确定 → ohc-run.py resolve-deps --list-available             （查看可用包）

configure 失败？
├─ 缺依赖 → 查 dependencies.md 编译顺序 → 先编依赖
├─ 平台不识别 → 改 config.guess/sub（build-systems.md §3.1）
├─ conftest pipe → configure 中 `| cat` 修复
└─ 其他 → 引擎匹配 graph/index.tsv → 按 E 编号查找
```

---

## §2 文件检索时机

| 触发场景 | 加载文件 | 何时 |
|---------|---------|------|
| 技能触发 | **SKILL.md**（本文档） | 每次 |
| 开始编译 | references/compile-guide.md | Step 2 前 |
| 预编译风险扫描 | knowledge/graph/pre-scan-rules.yaml | build Step 2.5（自动） |
| 编译出错 | knowledge/graph/index.tsv → graph/E*.kv | 错误发生时 |
| 缺少依赖 | ohc-run.py resolve-deps --list-available | init-build Step 7 |
| 失败处理 | references/failure-handling.md | R11+R12 流程 |
| 补丁生成 | references/patch-pipeline.md | Phase 3/4 |
| Staging 验证 | references/staging-verify.md | make install 后 |
| 打包阶段 | references/packaging-guide.md + knowledge/operations/packaging.md | Step 5 |
| 归档收尾 | references/archive-spec.md | Step 5.5 |
| 生成总览 | — | finish 内部自动 |
| 铁律详解 | references/iron-rules.md | 需要时 |
| 人类浏览错误 | knowledge/error-patterns.md | 人类查看 |
| 构建系统适配 | knowledge/operations/build-systems.md | configure 前 |
| 环境问题 | knowledge/operations/environment.md | 平台限制 |
| 依赖查询 | knowledge/operations/dependencies.md | 编译顺序 |
| 上下文裁剪 | references/context-trimming-protocol.md | 问题解决后 |

---

## §3 核心流程

### Step 1: ohc-run.py init-build — 全自动

```bash
$SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL] [--no-download] [--resume]
```

内部 **9 步**：registry 查询 → URL 确定 → 下载 → 解压 → 历史检索 → 骨架创建 → **依赖解析** → 环境检查 → 输出 `.build-context-<name>-<ver>`。

> **Step 7 依赖解析（新）**：自动检查编译所需的依赖是否已安装。如果有预编译包可用（来自 [cmd-pkgs](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/blob/main/README.md)），自动安装。无预编译包的依赖会发出警告。

**关键输出变量**：`BUILD_SOFTWARE`, `BUILD_VERSION`, `BUILD_SYSTEM`, `BUILD_SRC_DIR`, `BUILD_ARCHIVE_DIR`, `DEFAULT_PREFIX`（唯一权威安装前缀）。

### Step 2: AI 编译 — 唯一智能步骤

> **详解**: references/compile-guide.md
> **Staging 验证**: references/staging-verify.md
> **补丁规则**: references/patch-pipeline.md

```bash
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
```

> **⛔ R20 铁律：DESTDIR 模式（v8.0+）**
>
> | 变量 | 路径 | 用途 |
> |------|------|------|
> | `$DEFAULT_PREFIX` | `~/usr/local` | **configure --prefix 目标**（运行时路径，编译进二进制） |
> | `$TEST_PREFIX` | `~/tmp/test-install-{name}-{ver}` | **DESTDIR staging 根**（make install DESTDIR=） |
>
> **文件安装到**：`$TEST_PREFIX/$DEFAULT_PREFIX/bin/`, `$TEST_PREFIX/$DEFAULT_PREFIX/lib/` 等
>
> **二进制硬编码**：`$DEFAULT_PREFIX/share/misc/magic` → 运行时路径正确 ✅
>
> **流程**：`configure --prefix=$DEFAULT_PREFIX` → `make install DESTDIR=$TEST_PREFIX` → `package`（从 `$TEST_PREFIX/$DEFAULT_PREFIX/` 打包）→ 用户运行 `install.sh` 部署到 `$DEFAULT_PREFIX`

**执行顺序**：
1. `configure --prefix=$DEFAULT_PREFIX` → `make`
2. `make install DESTDIR=$TEST_PREFIX`（staging 隔离，打包用）
3. 安全弹窗(R7) → **make check**（必须执行，超时可 Ctrl+C 跳过）
4. Staging 验证
5. `ohc-run.py package`（预编译包制作）
6. ⭐ `make install`（不带 DESTDIR，安装到 `$DEFAULT_PREFIX`，模拟用户部署）
7. 用户验证（运行 `$DEFAULT_PREFIX/bin/*` 确认可用）
8. `ohc-run.py finish`

> **Step 6 的意义**：打包验证完成后，`make install` 将软件安装到本地 `~/usr/local`，模拟普通用户下载预编译包、运行 `install.sh` 后的真实状态。这一步能发现打包遗漏（缺库、路径错误、配置文件缺失）等问题。

> **make check 注意事项**：部分软件的测试套会卡住（如 coreutils cat-self、bash 多线程测试），遇到卡住可 `Ctrl+C` 跳过并在 PROGRESS.md 记录跳过原因。`make check` 的结果会写入 `reports/test-report.md`。

### HANDOFF 协议（脚本 → AI 交接格式）

> 脚本在需要 AI 介入时输出结构化交接块。AI 读到后按 `AI NEXT ACTIONS` 执行，完成后运行 `RESUME_CMD`。

```
╔═══ HANDOFF ══════════════════════════════════╗
║ EXIT_REASON: configure_failed                ║
║ EXIT_CODE: 2 (resumable) / 1 (fatal)         ║
║ STEP_FAILED: Step3                           ║
║ RESUME_CMD: python3 $SKILL_ROOT/scripts/ohc-run.py build ... --resume-from=Step3
║ KNOWLEDGE_HIT: E007 (config.guess) / none    ║
║ KNOWLEDGE_GAP: true/false                    ║
║ LOG_FILE: <日志路径>                          ║
║ SRC_DIR: <源码路径>                           ║
║ TASK_CARD: <任务卡路径>                       ║
║ AI NEXT ACTIONS:                             ║
║   1. 具体操作                                 ║
║   2. 运行 RESUME_CMD 继续                     ║
╚══════════════════════════════════════════════╝
```

**恢复编译时的规则**：
1. **新对话首选**：`python3 $SKILL_ROOT/scripts/ohc-run.py status` — 查看所有进行中编译，自动发现停在哪步、失败原因、HANDOFF 信息
2. 读取 `.handoff.json`（若存在）— 获取上一轮的完整上下文（失败原因、知识图谱命中、AI 操作指引）
3. **然后读 TASK_CARD.md**（了解之前完成了哪些步骤）
4. 执行 `AI NEXT ACTIONS`
5. `KNOWLEDGE_GAP: true` → 修复成功后必须沉淀到知识图谱
6. `EXIT_CODE: 1` → 不可恢复，需手动从头处理

### Step 2.5: 干净构建验证（⭐ R22 强制，脚本自动执行）

> **时机**：Phase 3 编译完成 + AI 自检通过 (R21) + refresh-patch 完成之后。
> **执行者**：`ohc-run.py clean-verify`（在 finish Step 3 内自动触发）。

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py clean-verify <软件名> <版本>
```

脚本自动执行：
1. 解压原始 tarball 到临时目录（不影响工作目录）
2. 应用 `patches/*.patch`
3. 运行 `./configure`（使用 manifest.yaml 中的 `configure_options`）
4. `make -j1`
5. `make install DESTDIR=...`
6. 检查产物完整性
7. 清理临时目录

**PASS** → 继续 finish 的 G1-G4 门禁。
**FAIL** → 输出 HANDOFF 块（见 staging-verify.md G0），AI 修复后重跑 clean-verify。

**设计目的**：暴露 Phase 3 中所有"手动操作但未固化为补丁/规则"的遗漏。

### Step 3: ohc-run.py finish — 6 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> success|partial|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/6] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/6] close-archive | 归档关闭 | exit 2 |
| [3/6] verify-build | 质量门禁 G1-G4 | ❌ 阻塞（未通过则 finish 失败） |
| [4/6] finalize-archive | 清理+校验+RELEASENOTE | 非致命 |
| [5/6] check-knowledge-gap | 知识完整性检查 | 非阻塞，提醒补充 |
| [6/6] gen_summary | 重新生成 SUMMARY.md | 非致命 |

**前置条件**：P1=test-report 存在, P2=Staging 验证完成, P3=预编译包已制作。

**状态值**：`success`（全通过）| `partial`（部分失败可分发）| `failed`（编译失败）。verify 通过升级状态，失败降级。

### Step 4: 质量门禁复查（可选）

```bash
$SKILL_ROOT/scripts/ohc-run.py verify-build <软件名> <版本>
```

5 道门禁：G0 干净构建验证（补丁自包含性）→ G1 二进制完整性 → G2 功能可用性 → G3 可移植性（RPATH/签名）→ G4 档案完整性。
G0 由 `ohc-run.py clean-verify` 执行，在 finish Step 3 自动触发。G0 FAIL 阻塞后续所有门禁。
正常流程已在 Step 3 自动执行。

### Step 5: 预编译包制作

> **详解**: references/packaging-guide.md
> **R19: 禁止手动打包！必须用 `ohc-run.py package`。** 手动 `tar czf` 会导致 ELF 未签名（鸿蒙上不可执行）、缺少 RPATH、未 strip 符号等问题。

verify PASS 后**必须**执行。按 packaging.md 10 步：收集 → 清理 → 链接替换 → 依赖收集 → RPATH → Strip → 签名 → 权限 → install.sh → tar.gz。

交付物：`{name}-{ver}-ohos-aarch64.tar.gz` + `debug.tar.gz` + `install.sh`。

### Step 5.5: 归档收口

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finalize-archive <软件名> <版本>
```

清理临时文件 + 6 项必填校验 + 一致性检查 + 最终报告。详见 references/archive-spec.md。

---

## §4 失败处理（R11+R12）

> **详解 + 反面案例**: references/failure-handling.md

```
失败发生
├─ [R11] 查归档：README.md → manifest.yaml → 软件级 README
├─ [R12] 匹配错误：引擎匹配 graph/index.tsv → E*.kv → 方案
├─ 缺依赖？→ ohc-run.py resolve-deps --install <name>（预编译包优先）
└─ 动手修复：归档+知识库都没有 → 记录新问题 → 修复 → 继续
```

**知识提取决策**：平台相关 → L1 立即写 knowledge/；构建模式 → L2 写 knowledge/；仅本软件 → L3 写 manifest。

### 4.1 历史信息纠正（R15）

> **核心问题**：历史编译记录可能包含错误方案（如用 `--build/--host` 绕过 config.guess），盲目复用会导致重复失败或引入隐患。

**触发条件**：以下任一情况出现时，进入纠错流程：
1. 历史记录的 configure 参数在本次失败
2. 历史记录包含禁用参数（`--build`, `--host`, `--target`）— 本平台是 native 编译
3. 历史记录缺少关键参数（如 `--without-shared`）
4. AI 在手动调试中发现历史方案有误

**纠错 4 步**：
```
1. 识别差距 → 对比历史参数 vs 本次成功参数，定位遗漏项
2. 手动编译 → 用正确参数完成编译（模式 B Step 2）
3. 回写历史 → 更新 manifest.yaml 的 configure_options + PROGRESS.md
4. 沉淀知识 → 如果是通用平台发现，写入 knowledge/ L1/L2
```

**常见平台必需参数**（R15 补充表）：

| 参数 | 适用场景 | 说明 |
|------|---------|------|
| `--without-shared` | ncurses（R4） | 防止 .so 导致系统崩溃 |
| `--no-asm` | OpenSSL | 无汇编支持 |
| `--without-bash-malloc` | bash | 使用系统 malloc |

**禁用参数**（native 编译，禁止使用）：

| 禁用项 | 错误原因 | 正确做法 |
|--------|---------|---------|
| `--build=...` | 本平台是 native 编译 | 修改 config.guess/config.sub（见 E007） |
| `--host=...` | 同上 | 同上 |
| `--target=...` | 同上 | 同上 |

---

## §5 知识图谱

### 5.1 目录结构

```
knowledge/graph/        # 结构化数据
├── index.tsv           # 主索引（80+ 条目）
├── principles.kv       # 编译原则（16 条）
├── pre-scan-rules.yaml # 预编译风险扫描规则集（闭环：编译新发现→自动回填）
├── E001.kv ~ E080.kv   # 错误模式条目
knowledge/doc/          # 人类可读文档
├── E001.md ~ E080.md
knowledge/error-patterns.md  # 人类浏览入口
```

### 5.2 引擎匹配（五阶段）

Phase A: index.tsv 粗筛 → Phase B: .kv 精排 → Phase C: 方案生成 → Phase D: 原则过滤 → Phase E: 输出执行。

### 5.3 管理命令

```bash
# 新增条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E{NNN}

# 更新条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph update E{NNN}

# 校验一致性
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate

# 归档/删除
python3 $SKILL_ROOT/scripts/ohc-run.py graph remove E{NNN} [--archive]

# 独立引擎匹配
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"

# 协作命令（协作者）
python3 $SKILL_ROOT/scripts/ohc-run.py submit --check <软件名> <版本>  # 本地自检（提交 PR 前）
python3 $SKILL_ROOT/scripts/ohc-run.py review <软件名> <版本>         # 主编本地辅助审核

# 依赖解析（预编译包）
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps <软件名>           # 检查依赖
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --install <软件名>  # 自动安装
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available    # 列出可用包
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --refresh           # 刷新远程索引
```

### 5.4 知识分层

| 层 | 归属 | 特征 | 写入时机 |
|----|------|------|---------|
| L1 平台真理 | knowledge/*.md | 任何软件可能遇到 | Phase 3 实时 |
| L2 模式经验 | knowledge/*.md 章节 | 同类构建系统复现 | Phase 3 实时 |
| L3 本版笔记 | manifest.yaml knowledge_gained | 仅本软件本版本 | Phase 3+4 |

### 5.5 上下文裁剪协议（⭐ 控制上下文膨胀）

问题解决后执行 4 步：沉淀知识 → 写索引行 → 裁剪遗忘 → 后续查图谱。

> 完整协议: references/context-trimming-protocol.md

---

## §6 归档规范摘要

> **完整规范**: references/archive-spec.md

### 目录结构

```
archives/{首字母}/{软件名}/          ← 软件级
├── README.md + RELEASENOTE.md + install.sh
└── {版本}/                         ← 版本级
    ├── manifest.yaml + PROGRESS.md
    ├── patches/*.patch
    ├── reports/
    └── packaging/*.tar.gz
```

### 必填文件

manifest.yaml, README.md, PROGRESS.md, RELEASENOTE.md, patches/, reports/, packaging/*.tar.gz

### 补丁命名

`NNNN-{文件名}.patch`，如 `0001-config.sub.patch`。

### 依赖顺序（批量编译参考）

按 `software-registry.yaml` 中的 category 分阶段编译，基础顺序: pkg-config → sed/coreutils/gawk → automake/libtool → ...（详见 knowledge/operations/dependencies.md）

---

## §7 Gotchas（鸿蒙关键陷阱）

| 陷阱 | 说明 | 对策 |
|------|------|------|
| /tmp 只读 | E002，写入报 Read-only | 用 `$TMPDIR` 或 `$HOME/tmp` |
| HMDFS 软链接 | 不能 ln -sf 覆盖 | `rm -f && ln -s` 或 wrapper |
| 安全弹窗 | 首次执行二进制弹确认框 | make install 后扫一遍 bin/ ✅ **HongMeng Kernel 1.12.0 已解决：已安装二进制可直接执行，不再弹窗** |
| chmod 不生效 | E046，SELinux 限制 | 记录为平台限制，不阻塞 |
| 未实现 syscall | E051，setreuid/chroot 等 | 加入 EXCLUDE_LIST 排除 |
| toybox sh 限制 | 缺 bash 特性，heredoc 差 | Python 化后已解决；仅限用户手动操作 shell 时注意 ✅ **HongMeng Kernel 1.12.0 已解决：GNU bash 5.3.0 已预装，heredoc 在 sh/bash 均正常** |
| ELF 签名 | 必须签名否则不可执行 | `python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf`，工具在 /data/service/hnp/bin/ |
| ncurses 共享库 | 编译为 .so 会导致系统崩溃 | `--without-shared`（R4） ✅ **HongMeng Kernel 1.12.0 已解决：已正确编译为静态库（--without-shared）** |

### 流程自省

发现 SKILL 自身问题时记录到 `reports/skill-feedback.md`：
```
### F{NNN}: {简短描述}
- 类别: 流程缺失/矛盾/脚本问题
- 严重: 🔴🟡🟢
- 建议: {怎么改}
```

---

## §8 多任务模式

### 8.1 架构

```
主任务（当前会话）
├── 编排调度：依赖排序 → 分阶段派发
├── 监控进度：dispatch status 查看各任务状态
├── 结果审计：review 各子任务输出
└── 最终提交：git add → commit → push → PR

子任务（createSubTask，异步并行）
└── 独立加载 skill → 完整编译流程 → 输出结果摘要
```

### 8.2 使用方式

**生成批量计划**:
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch plan zlib openssl wget
```
输出分阶段的 createSubTask 调用指令，主任务 AI 按此执行。

**查看任务状态**:
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch status zlib openssl wget
```

**生成子任务目标**（供 createSubTask 的 objective 参数）:
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch objective zlib 1.3.1
```

**生成调度脚本**（完整 createSubTask 调用序列）:
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch script zlib bzip2 openssl wget
```

### 8.3 主任务 AI 操作流程

```bash
# Step 1: 生成计划
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch plan zlib bzip2 openssl wget

# Step 2: 按计划创建异步子任务（Phase 0: 无依赖的软件）
# 直接调用 createSubTask 工具，objective 使用 dispatch 生成的文本

# Step 3: 等待 Phase 0 完成
# waitSubTask 检查结果

# Step 4: 创建 Phase 1 子任务（依赖 Phase 0 的软件）
# ...

# Step 5: 全部完成后审计
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch status zlib bzip2 openssl wget
python3 $SKILL_ROOT/scripts/ohc-run.py review zlib 1.3.1

# Step 6: 提交
git add . && git commit -m "feat: batch compile ..." && git push
```

### 8.4 子任务 isolation

每个子任务独立运行，互不干扰：
- 不同的 BUILD_SRC_DIR（~/tmp/builds/{name}-{ver}.work）
- 不同的 ARCHIVE_DIR（archives/{letter}/{name}/{ver}/）
- 独立的 .edit-tracker.json
- 独立的 .build-context-{name}-{ver}

唯一共享的资源：
- 项目根目录的 knowledge/（写草稿，不冲突）
- ~/usr/local（安装前缀，package 时独立 tar.gz）

**子任务知识提取职责（⭐ R17）**：
子任务不仅是编译执行者，也是知识发现者。编译过程中遇到的每个新错误模式：
1. 先用 `engine` 检查是否已有匹配条目
2. 无匹配 → 用 `graph add E{N} --draft` 创建草稿到 `knowledge/graph/draft/`
3. 草稿写入 `PROGRESS.md` 的知识提取记录
4. 主任务从 draft/ 目录收集所有草稿，审核后合并到正式图谱

`dispatch objective` 命令已内置此要求，生成的 objective 包含完整的 R17 草稿创建流程。

### 8.5 子命令一览

| 子命令 | 说明 |
|--------|------|
| `dispatch plan <sw1> <sw2> ...` | 生成分阶段执行计划 |
| `dispatch status <sw1> <sw2> ...` | 查看各软件编译状态 |
| `dispatch objective <sw> <ver>` | 输出子任务 objective 文本 |
| `dispatch script <sw1> <sw2> ...` | 生成 createSubTask 调度脚本 |

---

## §9 工具一览

| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `ohc-run.py build` | 14 步编译驱动（唯一入口） | ★ 主入口 |
| `ohc-run.py init-build` | 下载/解压/骨架/环境 | Step 1 |
| `pre_scan.py` | 预编译源码风险扫描（规则集 + musl 函数检测） | build Step 2.5 |
| `ohc-run.py finish` | 补丁+归档+verify+校验+知识+总结（6 步） | Step 3 |
| `ohc-run.py verify-build` | G1-G4 质量门禁 | finish 内部 / 可选复查 |
| `ohc-run.py clean-verify` | G0 干净构建验证 | finish Step 3 前置 / AI 手动 |
| `ohc-run.py refresh-patch` | 补丁管线 | finish 内部 |
| `ohc-run.py close-archive` | 归档关闭 | finish 内部 |
| `ohc-run.py finalize-archive` | 清理+校验+RELEASENOTE | finish 内部 |
| `ohc-run.py package` | 预编译包 10 步流程 | Step 5 |
| `ohc-run.py sign-elf` | ELF 签名 | 打包时 |
| `ohc-run.py init-archive` | 档架骨架创建 | init 内部 |
| `ohc-run.py check-env` | 环境检查 | init 内部 |
| `ohc-run.py search-url` | URL 搜索 5 策略 | init fallback |
| `ohc-run.py check-knowledge-gap` | 知识遗漏检查 | finish Step 5 |
| `ohc-run.py graph add` | 知识图谱新增条目 | AI 手动 |
| `ohc-run.py graph update` | 知识图谱更新条目 | AI 手动 |
| `ohc-run.py graph remove` | 知识图谱归档/删除 | AI 手动 |
| `ohc-run.py graph validate` | 图谱一致性校验 | add/update 内部 |
| `ohc-run.py engine` | 独立错误匹配引擎 | AI 手动 |
| `ohc-run.py status` | 跨对话编译状态扫描 | 恢复编译时 |
| `ohc-run.py handoff` | HANDOFF 上下文输出 | 恢复编译时 |
| `ohc-run.py summary` | 生成 SUMMARY.md | finish Step 6 |
| `ohc-run.py submit` | 提交前本地自检 | 协作者 PR 前 |
| `ohc-run.py review` | 本地审核辅助（12 项检查） | 主编 |
| `ohc-run.py post-merge` | 合并后重建索引（5 步） | 主编 |
| `ohc-run.py resolve-deps` | 查询/安装预编译依赖 | init-build Step 7 |
| `ohc-run.py track-edit` | 追踪/查询源码编辑记录 | 编译中每次修改源文件时 |
| `software-registry.yaml` | 软件元数据缓存 | init 读写 |

---

*SKILL.md v7.4 — 2026-04-13 — 新增 §8 多任务模式（dispatch 调度系统）*
