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
| 协作者（默认） | 直接使用 | 编译软件、提取知识、生成 conanfile.py、创建分支并提交 PR |
| 主编 | `OHC_ROLE=editor` | 审核 PR、合并知识、重建索引 |

**协作者 Git 铁律（违反=越权）**：
- ❌ 不要直接推送到 main 分支，必须创建功能分支
- ❌ 不要修改 `knowledge/graph/index.tsv`、`archives/_index.yaml`、`SUMMARY.md`
- ❌ 不要修改 `SKILL.md`、`references/`、`templates/`、`scripts/`、`ci/`
- ❌ 不要修改不属于自己负责的软件归档目录
- ✅ 新增知识用 `ohc-run.py graph add E{N} --draft`（写草稿目录）
- ✅ 完成后创建 PR：`git checkout -b feat/{软件名}-{版本}` → commit → push → GitCode PR

**Agent ID**：每个 Agent 实例自动获取 4 位随机标识（如 `A7F3`），用于分支后缀和草稿归属。可通过 `OHC_AGENT_ID` 环境变量预设。

---

## §1 快速参考

### 1.1 两套模式

**模式 A：Conan 驱动（推荐，适合已有 conanfile.py 的软件）**
```bash
# 直接用已有 conanfile.py 构建+测试
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> [<版本>]
# → 内含 13 步：init→patches→pre-scan→configure→make→install→staging→conan-init→conan-verify→finish→...
```

**模式 B：探索性编译（适合首次/复杂软件）**
```bash
# Step 1: 初始化（自动）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL]

# Step 2: 读取上下文，手动编译（唯一需要 AI 的步骤）
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX
make check  # 必须执行，超时可 Ctrl+C 跳过并记录原因

# Step 2.5: 生成 Conan 配方（⭐ v3.0 新核心步骤）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>

# Step 2.6: 验证 Conan 配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>

# Step 3: 收尾（6 步自动）
python3 $SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed|archived
```

**如何选择**：已有 conanfile.py / 简单编译 → 模式 A；首次编译 / 复杂依赖 / 需深度调试 → 模式 B。

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

### 1.2 铁律摘要（31 条，违反=bug）

| # | 规则 | 一句话 | 详解 |
|---|------|--------|------|
| R1 | 参数最少化 | 只需 `--prefix` | references/iron-rules.md |
| R2 | 探索阶段不生成 .patch | 只改源码+记录到 notes.md | references/patch-pipeline.md |
| R3 | 补丁只用 ohc-run.py refresh-patch | `ohc-run.py refresh-patch --auto` | references/patch-pipeline.md |
| R4 | 危险库静态编译 | conanfile.py `generate()` 中 `--without-shared` / `BUILD_SHARED_LIBS=OFF` | §7 Gotchas |
| R5 | 软链接验证可执行+禁止 ln -sf | `rm -f && ln -s` | §7 Gotchas |
| R6 | 只改源文件不改生成文件 | 用 `track-edit` 追踪 | references/iron-rules.md |
| R7 | 安全弹窗先触发再测试 | make install 后扫一遍 --version | references/compile-guide.md |
| R8 | 源码"四不"准则 | `#ifdef __OHOS__` 守卫 | references/iron-rules.md |
| R9 | 门禁 FAIL 禁标 success | 降级为 partial/failed | references/iron-rules.md |
| R10 | 临时文件用 $TMPDIR | 禁硬编码 /tmp（只读） | §7 Gotchas |
| R11 | 失败先查归档再动手 | 读 README.md + manifest.yaml | references/failure-handling.md |
| R12 | 先匹配错误模式再修复 | 引擎匹配 graph/index.tsv | references/failure-handling.md |
| R13 | 脚本用完整路径 | `python3 $SKILL_ROOT/scripts/ohc-run.py <cmd>` | §0 |
| R14 | 脚本失败=手动模式入口 | `--resume-from=StepN` 继续 | references/failure-handling.md |
| R15 | 历史仅供参考，不盲从 | 实际参数以本次编译为准 | §4.1 |
| R16 | 协作不越权 | 不推送 main，走 PR 流程 | knowledge/collaboration.md |
| R17 | 知识先草稿 | graph add --draft | knowledge/collaboration.md |
| R18 | 依赖先查预编译 | resolve-deps --install 优先 | §1.3 决策树 |
| R19 | **禁止手动打包** | 必须用 conan create + conan upload | references/iron-rules.md |
| R20 | ~~DESTDIR 模式~~（废弃） | Conan 自带隔离 | references/iron-rules.md |
| R21 | 探索结束自检零介入 | 所有手动操作已固化为 conanfile.py | references/iron-rules.md |
| R22 | finish 前必须通过 conan 验证 | `conan-verify` PASS | references/iron-rules.md |
| R23 | 平台检测优先于改生成文件 | 用 hints/config.guess/cmake | references/iron-rules.md |
| R24 | 归档清理：failed必删 | 无产物无补丁的归档无价值 | §6 |
| R25 | notes.md 防重复 | finish 自动清理旧记录 | §3 Step 3.1 |
| **R26** | **终端工具必须静态链接** | conanfile.py `generate()` `BUILD_SHARED_LIBS=OFF` / `-static` | references/iron-rules.md |
| **R27** | **依赖引用必须 @ohpcd/stable** | `self.requires("name/ver@ohpcd/stable")` | references/iron-rules.md |
| **R28** | **conanfile.py 必须有 test_package/** | 生成 conanfile.py 时同时生成 | references/iron-rules.md |
| **R29** | **conan_verify 通过才标 published** | `conan-verify` PASS → published | references/iron-rules.md |
| **R30** | **conan-verify 失败必须查询知识图谱** | G2 失败时 `run_engine()` 匹配 E-entry | references/iron-rules.md |
| **R31** | **知识图谱未命中必须生成草稿** | `knowledge/drafts/DRAFT-*.kv` 自动生成 | references/iron-rules.md |

### 1.3 决策树

```
新三方库？
├─ registry 有记录 → ohc-run.py init-build <name> <ver>
├─ 有 URL → ohc-run.py init-build <name> <ver> --url=URL
└─ 都没有 → ohc-run.py search-url <name> <ver> → 从候选选 URL

缺依赖？
├─ 从 cmd-pkgs README 查询预编译包 → curl install.sh | sh
├─ conan 制品仓有 → conan install --requires=name/ver@ohpcd/stable
└─ 无预编译包 → 查 dependencies.md 编译顺序 → 先编依赖

configure 失败？
├─ 缺依赖 → HANDOFF → AI 安装预编译包 → --resume-from=Step3
├─ 平台不识别 → 改 config.guess/sub（build-systems.md §3.1）
├─ conftest pipe → configure 中 `| cat` 修复
└─ 其他 → 引擎匹配 graph/index.tsv → 按 E 编号查找

编译成功 → 固化为 Conan 配方
├─ ohc-run.py conan-init <name> <ver>     生成 conanfile.py + conandata.yml + test_package/
├─ 检查生成的配方（requirements, package_info, 静态链接配置）
└─ ohc-run.py conan-verify <name> <ver>   验证配方可复现
```

> **⭐ R18 强化：预编译包优先原则**
> 
> 编译过程中发现的任何依赖缺失，**必须先查 cmd-pkgs README** 和 Conan 制品仓。
> 只有两者都没有才手动编译依赖。

---

## §2 文件检索时机

| 触发场景 | 加载文件 | 何时 |
|---------|---------|------|
| 技能触发 | **SKILL.md**（本文档） | 每次 |
| 开始编译 | references/compile-guide.md | Step 2 前 |
| 生成 Conan 配方 | templates/conanfile-*.py.tmpl + docs/CONANFILE_GUIDE.md | conan-init 时 |
| 验证 Conan 配方 | ci/conan/profiles/ohos-aarch64 | conan-verify 时 |
| 预编译风险扫描 | knowledge/graph/pre-scan-rules.yaml | build Step 2.5（自动） |
| 编译出错 | knowledge/graph/index.tsv → graph/E*.kv | 错误发生时 |
| 缺少依赖 | ohc-run.py resolve-deps --list-available | init-build Step 7 |
| 失败处理 | references/failure-handling.md | R11+R12 流程 |
| 补丁生成 | references/patch-pipeline.md | finish 内部 |
| 归档收尾 | knowledge/ARCHIVE-SPEC.md | finish 内部 |
| 铁律详解 | references/iron-rules.md | 需要时 |
| 软件迁移/新适配 | references/migration-guide.md | 迁移或新软件适配时 |
| 构建系统适配 | knowledge/operations/build-systems.md | configure 前 |
| CI 脚本契约 | docs/CI_SCRIPT_SPEC.md（外部参考） | ci/ 脚本修改时 |

---

## §3 核心流程

### Step 1: ohc-run.py init-build — 全自动

```bash
$SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL] [--no-download] [--resume]
```

内部 **9 步**：registry 查询 → URL 确定 → 下载 → 解压 → 历史检索 → 骨架创建 → **依赖解析** → 环境检查 → 输出 `.build-context-<name>-<ver>`。

**关键输出变量**：`BUILD_SOFTWARE`, `BUILD_VERSION`, `BUILD_SYSTEM`, `BUILD_SRC_DIR`, `BUILD_ARCHIVE_DIR`, `DEFAULT_PREFIX`。

### Step 2: AI 编译 — 唯一智能步骤

> **详解**: references/compile-guide.md

```bash
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
```

**执行顺序**：
1. `configure --prefix=$DEFAULT_PREFIX` → `make`
2. `make install DESTDIR=$TEST_PREFIX`（staging 隔离）
3. 安全弹窗(R7) → **make check**（必须执行，超时可 Ctrl+C 跳过）
4. Staging 验证

### HANDOFF 协议（脚本 → AI 交接格式）

> 脚本在需要 AI 介入时输出结构化交接块。AI 读到后按 `AI NEXT ACTIONS` 执行，完成后运行 `RESUME_CMD`。

```
╔═══ HANDOFF ══════════════════════════════════╗
║ EXIT_REASON: configure_failed                ║
║                | dependency_missing          ║
║                | build_tool_missing           ║
║                | command_mismatch             ║
║ EXIT_CODE: 2 (resumable) / 1 (fatal)         ║
║ STEP_FAILED: Step3                           ║
║ RESUME_CMD: python3 $SKILL_ROOT/scripts/ohc-run.py build ... --resume-from=Step3
║ KNOWLEDGE_HIT: E007 (config.guess) / none    ║
║ KNOWLEDGE_GAP: true/false                    ║
║ MISSING_DEPENDENCY: <软件名>                   ║
║ PRECOMPILED_AVAILABLE: yes/no                ║
║ LOG_FILE: <日志路径>                          ║
║ SRC_DIR: <源码路径>                           ║
║ AI NEXT ACTIONS:                             ║
║   1. 具体操作                                 ║
║   2. 运行 RESUME_CMD 继续                     ║
╚══════════════════════════════════════════════╝
```

### Step 2.5: 生成 Conan 配方（⭐ v3.0 新核心步骤）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>
```

从编译结果（manifest.yaml + notes.md + patches/）自动生成：
- **conanfile.py** — 可执行 Conan 2.x 配方（CI 唯一构建输入）
- **conandata.yml** — 源码 URL + SHA256 + 补丁声明
- **test_package/** — Conan L1 官方测试

**AI 必须检查**：
1. `requirements()` — 依赖列表是否完整，格式是否 `@ohpcd/stable`（R27）
2. `generate()` — 静态链接配置是否存在（R26）
3. `package_info()` — cpp_info.libs 是否正确
4. `conandata.yml` — sha256 是否填写

### Step 2.6: 验证 Conan 配方（⭐ v3.0 新核心步骤）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>
```

执行 7 道验证门禁（G1-G4 + L2/L4/L5）：

| 门禁 | 名称 | 检查内容 |
|------|------|---------|
| **G1** | 配方完整性 | conanfile.py + conandata.yml + test_package/ 存在且字段完整 |
| **G2** | conan create | 从干净源码构建，验证配方自包含性 |
| **G3** | 静态链接 (R26) | readelf -d 检查终端工具无非系统动态依赖 |
| **G4** | 产物完整性 | bin/lib/include 产物检查 |
| **L2** | 平台 smoke test | 运行构建产物 `--version`/`--help` 验证二进制可执行 |
| **L4** | 安全扫描 | readelf 检查 NX/PIE/RELRO/STACK_CANARY |
| **L5** | 产物基线 | SHA256 对比，首次保存基线，后续对比变化 |

**知识图谱集成（R30/R31）**：G2 失败时自动调用 `engine.py` 的 `run_engine()`：
- **命中** → 展示 E-entry 根因分析 + 修复命令 + 详细文档
- **未命中** → 自动生成 `knowledge/drafts/DRAFT-*.kv` 草稿，待人工/AI 审查提升

**G2 通过** = 配方可复现 = 可标记 `published`（R29）。

### Step 3: ohc-run.py finish — 6 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> published|built|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/6] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/6] close-archive | 归档关闭 | exit 2 |
| [3/6] conan-verify | Conan 配方验证（⭐ v3.0） | ❌ 阻塞 |
| [4/6] finalize-archive | 清理+校验+版本索引 | 非致命 |
| [5/6] check-knowledge-gap | 知识完整性检查 | 非阻塞 |
| [6/6] gen_summary | 重新生成 SUMMARY.md | 非致命 |

**前置条件**：P1=test-report 存在, P2=Staging 验证完成, P3=conanfile.py 存在（v3.0）。

**状态值**：`published`（conan-verify 通过 + CI upload 完成）| `built`（conan-verify 通过，未 upload）| `failed`（编译或 conan-verify 失败）| `archived`（旧版本归档）。

### Step 4: 质量门禁复查（可选）

```bash
$SKILL_ROOT/scripts/ohc-run.py verify-build <软件名> <版本>
```

对于有 conanfile.py 的版本，finish 已自动调用 conan-verify。此命令用于独立复查。

### Step 5: CI 流水线（外部驱动，无 AI 参与）

> **⚠️ CI/SKILL 边界**：CI 脚本是纯 zsh + conan，**不依赖** ohc-run.py、engine.py、知识图谱、草稿机制。
> AI 工具（探索编译、知识图谱查询、conan-verify）仅在本地开发环境使用。

**两仓分工**：

| 仓库 | 定位 | 内容 |
|------|------|------|
| `build_in_harmonyos`（本仓） | AI 知识库 + 配方仓 + CI 脚本 | SKILL.md、scripts/ohc/、knowledge/、archives/、templates/、ci/ |
| `build_in_harmonyos_ci` | CI 引擎（Buildbot） | master.cfg、worker 配置、CI_SCRIPT_SPEC.md |

CI Worker 克隆本仓后直接执行 `ci/` 脚本，无需 Python SKILL 环境。

| 流水线 | 触发条件 | 执行步骤 | Upload |
|--------|----------|----------|--------|
| PR 校验 | PR 创建/更新 | setup.sh → build_and_test.sh | ❌ 不上传 |
| 正式发布 | PR 合并到 main | setup.sh → build_and_test.sh → upload.sh → sign.sh | ✅ 上传到 CNB |

```
ci/conan/setup.sh          → Conan 环境初始化 + profile + remote
ci/conan/build_and_test.sh  → conan create + L4 安全扫描 + L5 产物检查（纯 shell，无 AI）
ci/conan/upload.sh          → conan upload 到 CNB 制品仓（仅 release，密钥在执行机）
ci/artifacts/sign.sh        → GPG 签名（非阻塞）
```

**Upload 安全边界**：Conan 制品仓密钥（`CONAN_REMOTE_USER`/`CONAN_REMOTE_PASS`）仅存储在 CI 执行机，
由 Buildbot 注入环境变量。PR 校验流水线**不执行 upload**，只有合并到 main 后的正式发布流水线才 upload。
开发者机器和本仓代码中**不可见**密钥。

**CI 只读取的归档文件**（4 个，最小集）：
- `conanfile.py` — 构建配方（CI 唯一构建输入）
- `conandata.yml` — 源码 URL + SHA256 + 补丁声明
- `test_package/` — L1 测试
- `patches/` — 补丁文件

**CI 不读取的文件**（AI 侧元数据，不影响 CI）：
- `manifest.yaml` — AI 生成 conanfile.py 的输入 + 状态追踪
- `notes.md` — AI 适配笔记
- `reports/` — 验证报告

---

## §4 失败处理（R11+R12）

> **详解 + 反面案例**: references/failure-handling.md

```
失败发生
├─ [R11] 查归档：README.md → manifest.yaml → conanfile.py
├─ [R12] 匹配错误：引擎匹配 graph/index.tsv → E*.kv → 方案
├─ 缺依赖？→ conan install 或 resolve-deps --install
└─ 动手修复：归档+知识库都没有 → 记录新问题 → 修复 → 继续
```

### 4.1 历史信息纠正（R15）

> **核心问题**：历史编译记录可能包含错误方案。

**纠错 4 步**：
1. 识别差距 → 对比历史参数 vs 本次成功参数
2. 手动编译 → 用正确参数完成编译
3. 回写历史 → 更新 conanfile.py + manifest.yaml + notes.md
4. 沉淀知识 → 通用平台发现写入 knowledge/ L1/L2

**禁用参数**（native 编译）：
| 禁用项 | 正确做法 |
|--------|---------|
| `--build=...` | 修改 config.guess/config.sub |
| `--host=...` | 同上 |
| `--target=...` | 同上 |

---

## §5 知识图谱

### 5.1 目录结构

```
knowledge/graph/        # 结构化数据
├── index.tsv           # 主索引（100+ 条目）
├── principles.kv       # 编译原则（20 条）
├── pre-scan-rules.yaml # 预编译风险扫描规则集
├── E001.kv ~ E080.kv   # 错误模式条目
knowledge/drafts/       # 草稿目录（conan-verify 自动生成，R31）
├── README.md           # 草稿→正式 E-entry 提升流程
├── DRAFT-001.kv ~      # 待审查的草稿条目
knowledge/doc/          # 人类可读文档
├── E001.md ~ E080.md
knowledge/error-patterns.md  # 人类浏览入口
```

### 5.2 引擎匹配（五阶段）

Phase A: index.tsv 粗筛 → Phase B: .kv 精排 → Phase C: 方案生成 → Phase D: 原则过滤 → Phase E: 输出执行。

### 5.3 管理命令

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py graph add E{NNN}             # 新增条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph update E{NNN}          # 更新条目
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate                # 校验一致性
python3 $SKILL_ROOT/scripts/ohc-run.py engine "错误日志"             # 独立引擎匹配
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件> <版本>      # 生成 Conan 配方 ⭐ v3.0
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件> <版本>    # 验证 Conan 配方 ⭐ v3.0
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps <软件名>          # 检查依赖
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --install <软件名> # 自动安装
```

### 5.4 知识分层

| 层 | 归属 | 特征 | 写入时机 |
|----|------|------|---------|
| L1 平台真理 | knowledge/*.md | 任何软件可能遇到 | 探索阶段实时 |
| L2 模式经验 | knowledge/*.md 章节 | 同类构建系统复现 | 探索阶段实时 |
| L3 本版笔记 | conanfile.py + manifest.yaml | 仅本软件本版本 | 探索阶段+固化阶段 |

---

## §6 归档规范摘要

> **完整规范**: knowledge/ARCHIVE-SPEC.md (v3.0)

### 目录结构 (v3.0)

```
archives/{letter}/{name}/
  ├── manifest.yaml              # 软件级元数据 + 版本索引
  ├── README.md                  # 软件描述
  └── {version}/
      ├── conanfile.py           # 【CI 输入】Conan 配方
      ├── conandata.yml          # 【CI 输入】源码 + 补丁声明
      ├── test_package/          # 【CI 输入】Conan L1 测试
      ├── patches/               # 【CI 输入】补丁文件
      ├── manifest.yaml          # 【AI 元数据】编译元数据 + 状态
      ├── notes.md               # 【AI 元数据】适配笔记
      └── reports/               # 【AI 元数据】验证报告
```

### 文件分类

| 分类 | 文件 | CI 读取 | AI 读取 | 说明 |
|------|------|---------|---------|------|
| CI 输入 | conanfile.py | ✅ | ✅ | CI 唯一构建输入 |
| CI 输入 | conandata.yml | ✅ | ✅ | 源码 URL + SHA256 |
| CI 输入 | test_package/ | ✅ | ✅ | Conan L1 测试 |
| CI 输入 | patches/ | ✅ | ✅ | 补丁文件 |
| AI 元数据 | manifest.yaml | ❌ | ✅ | conan-init 输入 + 状态 |
| AI 元数据 | notes.md | ❌ | ✅ | 适配过程笔记 |
| AI 元数据 | reports/ | ❌ | ✅ | 验证报告 |

### 状态定义 (v3.0)

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| `published` | conan-verify 通过 + CI conan upload 完成 | conan-verify PASS + upload 成功 |
| `built` | conan-verify 通过，未上传制品仓 | conan-verify PASS，未 upload |
| `failed` | 编译失败或 conan-verify 失败 | 探索失败或 conan create 失败 |
| `archived` | 旧版本归档 | 新版本发布后 |

### 归档清理规则（R24）

| 状态 | 产物 | 补丁 | 处理 |
|------|------|------|------|
| published | ✅ conanfile.py | 可能有 | 保留 |
| built (有 conanfile.py) | ✅ | 有 | 保留 |
| built (空骨架) | ❌ | ❌ | 删除 |
| failed | ❌ | ❌ | 删除 |

---

## §7 Gotchas（鸿蒙关键陷阱）

| 陷阱 | 说明 | 对策 |
|------|------|------|
| /tmp 只读 | E002，写入报 Read-only | 用 `$TMPDIR` 或 `$HOME/tmp` |
| HMDFS 软链接 | 不能 ln -sf 覆盖 | `rm -f && ln -s` 或 wrapper |
| 安全弹窗 | 首次执行二进制弹确认框 | make install 后扫一遍 bin/ |
| chmod 不生效 | E046，SELinux 限制 | 记录为平台限制，不阻塞 |
| 未实现 syscall | E051，setreuid/chroot 等 | 加入 EXCLUDE_LIST 排除 |
| ELF 签名 | 必须签名否则不可执行 | CI 流水线 `ci/artifacts/sign.sh` |
| ncurses 共享库 | 编译为 .so 会导致系统崩溃 | conanfile.py `generate()` `--without-shared`（R4） |
| 静态链接 | DevBox 只拷 bin/，无 lib/ | conanfile.py `BUILD_SHARED_LIBS=OFF`（R26） |
| RPATH 解析 | 鸿蒙 `$ORIGIN/../lib` 不稳定 | 终端工具强制静态链接（R26） |

### 流程自省

发现 SKILL 自身问题时记录到 `reports/skill-feedback.md`。

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
└── 独立加载 skill → 完整编译流程 → 生成 conanfile.py → 输出结果摘要
```

### 8.2 使用方式

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch plan zlib openssl wget
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch status zlib openssl wget
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch objective zlib 1.3.1
python3 $SKILL_ROOT/scripts/ohc-run.py dispatch script zlib bzip2 openssl wget
```

---

## §9 工具一览

| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `ohc-run.py build` | 13 步编译驱动（含 conan 配方生成+验证） | ★ 主入口 |
| `ohc-run.py init-build` | 下载/解压/骨架/环境 | Step 1 |
| `ohc-run.py conan-init` | 生成 conanfile.py + conandata.yml + test_package/ ⭐ | Step 9 (v3.0) |
| `ohc-run.py conan-verify` | conan create + 知识图谱(R30) + 草稿(R31) + G1-G4 + L2/L4/L5 ⭐ | Step 10 / finish Step 3 |
| `pre_scan.py` | 预编译源码风险扫描 | build Step 2.5 |
| `ohc-run.py finish` | 补丁+归档+conan-verify+校验+知识+摘要（6 步） | Step 3 |
| `ohc-run.py verify-build` | 传统 G1-G4 门禁（遗留兼容） | 可选复查 |
| `ohc-run.py clean-verify` | G0 干净构建验证 | finish 前置 |
| `ohc-run.py refresh-patch` | 补丁管线 | finish 内部 |
| `ohc-run.py close-archive` | 归档关闭 | finish 内部 |
| `ohc-run.py finalize-archive` | 清理+校验+版本索引 | finish 内部 |
| `ohc-run.py sign-elf` | ~~ELF 签名~~（已移除，由 ci/artifacts/sign.sh 替代） | — |
| `ohc-run.py package` | ~~手动打包~~（已移除，由 conan create 替代） | — |
| `ohc-run.py init-archive` | 档架骨架创建 | init 内部 |
| `ohc-run.py check-env` | 环境检查 | init 内部 |
| `ohc-run.py search-url` | URL 搜索 5 策略 | init fallback |
| `ohc-run.py check-knowledge-gap` | 知识遗漏检查 | finish Step 5 |
| `ohc-run.py graph add` | 知识图谱新增条目 | AI 手动 |
| `ohc-run.py graph update` | 知识图谱更新条目 | AI 手动 |
| `ohc-run.py engine` | 独立错误匹配引擎 | AI 手动 |
| `ohc-run.py status` | 跨对话编译状态扫描 | 恢复编译时 |
| `ohc-run.py handoff` | HANDOFF 上下文输出 | 恢复编译时 |
| `ohc-run.py summary` | 生成 SUMMARY.md | finish Step 6 |
| `ohc-run.py submit` | 提交前本地自检 | 协作者 PR 前 |
| `ohc-run.py review` | 本地审核辅助 | 主编 |
| `ohc-run.py resolve-deps` | 查询/安装预编译依赖 | init-build Step 7 |
| `ohc-run.py track-edit` | 追踪/查询源码编辑记录 | 编译中每次修改源文件时 |
| `software-registry.yaml` | 软件元数据缓存 | init 读写 |

### CI 脚本（ci/ 目录，由 Buildbot Worker 执行）

| 脚本 | 用途 |
|------|------|
| `ci/conan/setup.sh` | Conan 环境初始化 + profile + remote |
| `ci/conan/build_and_test.sh` | conan create + L4/L5 检查（纯 shell，无 AI） |
| `ci/conan/upload.sh` | conan upload 到 CNB 制品仓（仅 release） |
| `ci/artifacts/sign.sh` | GPG 签名（非阻塞） |
| `ci/conan/profiles/ohos-aarch64` | Conan 编译 profile |

---

*SKILL.md v8.2 — 2026-06-22 — 明确 CI/SKILL 边界（CI 无 AI、无 ohc-run.py）、归档文件 CI/AI 分类、Upload 安全边界、CI 脚本回退纯 shell*
