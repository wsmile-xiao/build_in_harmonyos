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

---

## §1 快速参考

### 1.1 两套模式

**模式 A：全自动（推荐，适合大多数三方库）**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py build <软件名> [<版本>]
# → 内含 13 步：init→patches→configure→make→install→staging→package→deploy→finish→...
```
脚本遇到 configure/make 错误时自动输出 HANDOFF 块，AI 修复后 `--resume-from=StepN` 继续。

**模式 B：AI 手动编译（适合复杂/首次编译的软件）**
```bash
# Step 1: 初始化（自动）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build <软件名> [<版本>] [--url=URL]

# Step 2: 读取上下文，手动编译（唯一需要 AI 的步骤）
# 读取 .build-context-<name>-<ver> 获取 BUILD_SRC_DIR, TEST_PREFIX 等变量
cd $BUILD_SRC_DIR
./configure --prefix=$TEST_PREFIX && make -j$(nproc) && make install

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

### 1.2 铁律摘要（14 条，违反=bug）

| # | 规则 | 一句话 | 详解 |
|---|------|--------|------|
| R1 | 参数最少化 | 只需 `--prefix` | references/iron-rules.md |
| R2 | Phase 3 不生成 .patch | 只改源码+记录 PROGRESS | references/patch-pipeline.md |
| R3 | 补丁只用 ohc-run.py refresh-patch | `ohc-run.py refresh-patch --auto` | references/patch-pipeline.md |
| R4 | 危险库静态编译 | ncurses `--without-shared` | §7 Gotchas |
| R5 | 软链接验证可执行+禁止 ln -sf | `rm -f && ln -s` | §7 Gotchas |
| R6 | 禁止改生成文件 | 只改 configure.ac/CMakeLists/源码 | references/iron-rules.md |
| R7 | 安全弹窗先触发再测试 | make install 后扫一遍 --version | references/compile-guide.md |
| R8 | 源码"四不"准则 | `#ifdef __OHOS__` 守卫 | references/iron-rules.md |
| R9 | 门禁 FAIL 禁标 success | 降级为 partial/failed | references/iron-rules.md |
| R10 | 临时文件用 $TMPDIR | 禁硬编码 /tmp（只读） | §7 Gotchas |
| R11 | 失败先查归档再动手 | 读 README.md + manifest.yaml | references/failure-handling.md |
| R12 | 先匹配错误模式再修复 | 引擎匹配 graph/index.tsv | references/failure-handling.md |
| R13 | 脚本用完整路径 | `python3 $SKILL_ROOT/scripts/ohc-run.py <cmd>` | §0 |
| R14 | 脚本失败=手动模式入口 | `--resume-from=StepN` 继续 | references/failure-handling.md |

### 1.3 决策树

```
新三方库？
├─ registry 有记录 → ohc-run.py init-build <name> <ver>           （全自动）
├─ 有 URL → ohc-run.py init-build <name> <ver> --url=URL          （自动注册）
└─ 都没有 → ohc-run.py search-url <name> <ver>           → 从候选选 URL

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
| 编译出错 | knowledge/graph/index.tsv → graph/E*.kv | 错误发生时 |
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

内部 8 步：registry 查询 → URL 确定 → 下载 → 解压 → 历史检索 → 骨架创建 → 环境检查 → 输出 `.build-context-<name>-<ver>`。

**关键输出变量**：`BUILD_SOFTWARE`, `BUILD_VERSION`, `BUILD_SYSTEM`, `BUILD_SRC_DIR`, `BUILD_ARCHIVE_DIR`, `DEFAULT_PREFIX`（唯一权威安装前缀）。

### Step 2: AI 编译 — 唯一智能步骤

> **详解**: references/compile-guide.md
> **Staging 验证**: references/staging-verify.md
> **补丁规则**: references/patch-pipeline.md

```bash
source .build-context-<name>-<ver>
cd $BUILD_SRC_DIR
./configure --prefix=$TEST_PREFIX && make -j1 && make install
```

**执行顺序**：configure → make → install(到 $TEST_PREFIX) → 安全弹窗(R7) → make check → Staging 验证 → package → finish。

$TEST_PREFIX 是隔离 staging 目录，$DEFAULT_PREFIX 是最终部署目标（由 install.sh 写入）。

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

### Step 3: ohc-run.py finish — 6 步自动收尾

```bash
$SKILL_ROOT/scripts/ohc-run.py finish <软件名> <版本> success|partial|failed
```

| 步骤 | 内容 | 失败处理 |
|------|------|---------|
| [1/6] refresh-patch --auto | 补丁生成 | 跳过，继续归档 |
| [2/6] close-archive | 归档关闭 | exit 2 |
| [3/6] verify-build | 质量门禁 G1-G4 | 非阻塞，降级状态 |
| [4/6] finalize-archive | 清理+校验+RELEASENOTE | 非致命 |
| [5/6] check-knowledge-gap | 知识完整性检查 | 非阻塞，提醒补充 |
| [6/6] gen_summary | 重新生成 SUMMARY.md | 非致命 |

**前置条件**：P1=test-report 存在, P2=Staging 验证完成, P3=预编译包已制作。

**状态值**：`success`（全通过）| `partial`（部分失败可分发）| `failed`（编译失败）。verify 通过升级状态，失败降级。

### Step 4: 质量门禁复查（可选）

```bash
$SKILL_ROOT/scripts/ohc-run.py verify-build <软件名> <版本>
```

4 道门禁：G1 二进制完整性 → G2 功能可用性 → G3 可移植性（RPATH/签名）→ G4 档案完整性。正常流程已在 Step 3 自动执行。

### Step 5: 预编译包制作

> **详解**: references/packaging-guide.md

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
└─ 动手修复：归档+知识库都没有 → 记录新问题 → 修复 → 继续
```

**知识提取决策**：平台相关 → L1 立即写 knowledge/；构建模式 → L2 写 knowledge/；仅本软件 → L3 写 manifest。

---

## §5 知识图谱

### 5.1 目录结构

```
knowledge/graph/        # 结构化数据
├── index.tsv           # 主索引（80+ 条目）
├── principles.kv       # 编译原则（16 条）
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

manifest.yaml, README.md, PROGRESS.md, RELEASENOTE.md, install.sh, patches/, reports/, packaging/*.tar.gz

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
| 安全弹窗 | 首次执行二进制弹确认框 | make install 后扫一遍 bin/ |
| chmod 不生效 | E046，SELinux 限制 | 记录为平台限制，不阻塞 |
| 未实现 syscall | E051，setreuid/chroot 等 | 加入 EXCLUDE_LIST 排除 |
| toybox sh 限制 | 缺 bash 特性，heredoc 差 | Python 化后已解决；仅限用户手动操作 shell 时注意 |
| ELF 签名 | 必须签名否则不可执行 | `python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf`，工具在 /data/service/hnp/bin/ |
| ncurses 共享库 | 编译为 .so 会导致系统崩溃 | `--without-shared`（R4） |

### 流程自省

发现 SKILL 自身问题时记录到 `reports/skill-feedback.md`：
```
### F{NNN}: {简短描述}
- 类别: 流程缺失/矛盾/脚本问题
- 严重: 🔴🟡🟢
- 建议: {怎么改}
```

---

## §8 工具一览

| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `ohc-run.py build` | 13 步编译驱动（唯一入口） | ★ 主入口 |
| `ohc-run.py init-build` | 下载/解压/骨架/环境 | Step 1 |
| `ohc-run.py finish` | 补丁+归档+verify+校验+知识+总结（6 步） | Step 3 |
| `ohc-run.py verify-build` | G1-G4 质量门禁 | finish 内部 / 可选复查 |
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
| `software-registry.yaml` | 软件元数据缓存 | init 读写 |

---

*SKILL.md v7.0 — 2026-04-11 — Python 统一入口（ohc-run.py）全量实现*
