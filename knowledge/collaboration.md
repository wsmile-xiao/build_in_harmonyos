# 多 Agent 协作与任务编排规范

> **用途**: 定义多 Agent 实例协作编译、子任务拆分、审核合并的完整工作流，以及从历史执行中提炼的流程改进规则。
> **覆盖范围**: 协作架构、提交单规范、子任务拆分原则、质量保障、工作流改进规则、防遗忘策略。

---

# 第一部分：协作架构与工作流

> 本部分定义了多个 AI 实例协作编译开源软件、提交知识、审核合并的完整工作流。
> 核心机制：**Git + GitCode PR + 随机 Agent ID**，基于分支和 Pull Request 实现协作。

## §1 协作模式概述

本系统运行在 OpenDesk 的 skill 环境中，多个 Agent 实例基于 **Git + GitCode PR** 工作流实现协作。协作者在独立分支上工作，通过创建 Pull Request（PR）提交工作成果，主编在 GitCode 平台上审核并合并 PR。

### 两种角色模式

| 模式 | 对应角色 | 核心职责 | 数量 |
|------|---------|---------|------|
| **协作者模式**（默认） | 贡献者 Agent | 创建分支、编译软件、编写补丁、提取知识、提交 PR | 多个 |
| **主编模式** | 主编 Agent | 审核 PR、知识去重、编号统一、合并 PR、重建索引 | 1 个 |

### 切换方式

```bash
# 方式一：环境变量（推荐，启动时指定）
export OHC_ROLE=editor

# 方式二：运行时切换
python3 scripts/ohc-run.py mode editor    # 切换为主编模式
python3 scripts/ohc-run.py mode contributor  # 切回协作者模式（默认）

# 查看当前模式
python3 scripts/ohc-run.py mode
```

### 角色对比

| 维度 | 协作者 | 主编 |
|------|--------|------|
| **可写区域** | 自己的 archive 目录 + knowledge/graph/draft/ | 所有区域 + 索引文件 |
| **禁止写入** | knowledge/graph/ 正式目录、index.tsv、_index.yaml、SUMMARY.md | 无限制 |
| **提交方式** | 创建 Git 分支，提交 PR 到 GitCode | 审核 PR，在平台上接受或拒绝 |
| **知识操作** | 写草稿到 draft/（在分支上提交） | 审核草稿、去重、编号、合并 PR 后移入正式目录 |
| **索引操作** | 只读 | 合并 PR 后重建 index.tsv、_index.yaml、SUMMARY.md |

## §2 Agent ID 机制

每个 Agent 实例拥有一个 **4 位十六进制 ID**（如 `A7F3`），用于标识提交来源、归属草稿文件、记录协作历史。

### ID 生成优先级

```
1. 环境变量 OHC_AGENT_ID        → 如果已设置，直接使用
2. 时间戳哈希随机生成            → 每次调用基于当前时间戳 MD5 哈希生成，不持久化
```

### 生成机制说明

**为什么不使用 .agent-id 文件持久化？**

- 多个协作者可能共享同一个 skill 目录（如远程服务器）
- 文件持久化会导致 ID 冲突（协作者 A 的 ID 被协作者 B 读取）
- 时间戳哈希随机生成确保每次调用都有不同的 ID，避免冲突

### 自动生成示例

```bash
# 每次调用都生成新的 ID
$ python3 scripts/ohc-run.py whoami
Agent ID: A7F3 (timestamp-hash generated)
Role: contributor
Archive: (not assigned)

# 同一会话中多次调用会生成不同 ID
$ python3 scripts/ohc-run.py whoami
Agent ID: B2E8 (timestamp-hash generated)
Role: contributor
Archive: archives/c/curl/8.7.1

# 如需固定 ID，使用环境变量
$ export OHC_AGENT_ID=F3A2
$ python3 scripts/ohc-run.py whoami
Agent ID: F3A2 (from OHC_AGENT_ID)
Role: contributor
Archive: archives/c/curl/8.7.1
```

### 用途

| 场景 | 用途说明 |
|------|---------|
| **PR 标识** | contributor_id 字段记录由哪个 Agent 提交 |
| **notes.md 记录** | 标注当前正在编译此软件的 Agent ID |
| **草稿文件归属** | knowledge/graph/draft/ 下的草稿文件包含 contributor_id |
| **协作审计** | 通过 Agent ID 追溯每项工作的来源 |
| **主编审核日志** | 记录哪个主编审核、批准了哪些 PR |

## §3 文件所有权矩阵

### 所有权分区

| 分区 | 路径 | 协作者 | 主编 | 说明 |
|------|------|--------|------|------|
| **贡献区** | `archives/{letter}/{name}/{version}/` | ✅ 独占读写（分支上） | ✅ 审核时读取 | 不同软件目录天然隔离，每个协作者只操作自己负责的目录 |
| **Git 分支** | `feat/{software}-{version}` | ✅ 创建和推送分支 | ✅ fetch 并审核 | 协作者在独立分支上工作，主编通过 git fetch 获取分支内容进行审核 |
| **GitCode PR 状态** | GitCode 平台 | ✅ 创建 PR | ✅ 审核并接受/拒绝 PR | PR 状态（open/merged/closed）在 GitCode 平台上管理 |
| **共享知识区（草稿）** | `knowledge/graph/draft/` | ✅ 写入草稿（分支上） | ✅ 审核草稿 | 协作者在分支上写入新知识草稿，主编在 PR 审核时检查 |
| **共享知识区（正式）** | `knowledge/graph/*.yaml` `knowledge/*.md` | ❌ 只读 | ✅ 独占写入（main 分支） | 只有主编能修改正式知识文件 |
| **编辑独占区** | `knowledge/graph/index.tsv` `knowledge/graph/_index.yaml` `SUMMARY.md` | ❌ 禁止修改 | ✅ 独占写入 | 索引文件只由主编在合并 PR 后重建 |
| **反馈渠道（版本级）** | `archives/{letter}/{name}/{version}/feedback.md` | ✅ 写入 | ✅ 读取 | 协作者在编译中发现的问题记录在此 |
| **反馈渠道（根级）** | `reports/skill-feedback.md` | ❌ 禁止修改 | ✅ 收割汇总 | 主编从各版本级 feedback.md 汇总至此 |

### Git 操作权限说明

| 操作 | 协作者 | 主编 | 说明 |
|------|--------|------|------|
| `git checkout -b feat/xxx` | ✅ 允许 | ✅ 允许 | 协作者创建功能分支 |
| `git push origin feat/xxx` | ✅ 允许 | ✅ 允许 | 协作者推送自己的分支 |
| `git push origin main` | ❌ 禁止 | ✅ 允许 | 只有主编能推送 main 分支 |
| 在 GitCode 创建 PR | ✅ 允许 | ✅ 允许 | 协作者创建 PR 请求合并 |
| 在 GitCode 合并 PR | ❌ 禁止 | ✅ 允许 | 只有主编能合并 PR |
| `git merge main`（本地） | ✅ 允许（rebase） | ✅ 允许 | 协作者通过 rebase 同步 main |
| 直接修改 main 分支文件 | ❌ 禁止 | ✅ 允许 | 主编可通过 hotfix 直接修改 main |

### 关键原则

1. **Git 分支天然隔离**：每个协作者在自己的 `feat/{software}-{version}` 分支上工作，通过 PR 请求合并，避免直接修改 main
2. **知识通过草稿隔离**：协作者不直接修改 `knowledge/` 正式文件，而是写入 `knowledge/graph/draft/`（在分支上提交），由主编审核后通过合并 PR 移入
3. **索引文件主编独占**：`index.tsv`、`_index.yaml`、`SUMMARY.md` 只在主编合并 PR 后自动重建，协作者永不触碰

## §4 PR 规范（GitCode Pull Request）

> 替代原有的提交单（submission）机制。所有协作者通过 Git 分支和 GitCode PR 提交工作成果。

### PR 标题格式

```
feat: 编译 {软件名} {版本} - {状态}
```

示例：
```
feat: 编译 curl 8.7.1 - success
feat: 编译 python 3.9.25 - partial (89.4% 测试通过)
fix: 修复 E055 错误模式描述不准确
opt: 优化 knowledge 索引重建流程
```

### PR 描述三要素

每个 PR 的描述必须包含以下三个部分：

```markdown
## 背景
编译 curl 8.7.1，目标平台 HarmonyOS NEXT (musl libc)。
已有知识库条目：§15 (autotools)、§19 (HarmonyOS 特性)。

## 修改
- 新增补丁：0001-config.guess-harmonyos.patch（平台识别）
- 新增补丁：0002-fix-musl-compat.patch（musl 兼容性）
- 新增知识草稿：E055, E056, E057（knowledge/graph/draft/）
- 更新 notes.md（编译过程记录）
- 更新 manifest.yaml（构建信息和测试结果）

## 测试
- make check: 29 passed / 6 failed / 35 total
- 失败原因：SELinux 软链接限制（非功能问题）
- 本地自检通过：ohc-run.py submit --check curl 8.7.1
```

### Squash 合并说明

主编在 GitCode 平台上合并 PR 时，默认使用 **Squash Merge**：
- 将分支上的所有提交压缩为一个提交，保持 main 分支历史整洁
- 压缩后的提交消息格式：`feat: 编译 {软件名} {版本} - {状态}`
- 如需保留完整提交历史，在 PR 标题前添加 `[NOSQUASH]` 标记

### PR 生命周期

```
协作者编译完成
      │
      ▼
ohc-run.py submit --check <name> <version>    # 本地自检
      │
      ▼ 通过
git add . && git commit -m "feat: 编译 {name} {version} - {status}"
git rebase main && git push origin feat/{software}-{version}
      │
      ▼
在 GitCode 上创建 PR（填写标题 + 描述三要素）
      │
      ▼
GitCode PR 状态：Open
      │
      ├──► 主编本地审核 ──► 通过 ──► GitCode 平台接受 PR（Squash Merge）
      │                                    │
      │                                    ├─ 本地 git pull origin main
      │                                    ├─ 移动 draft → 正式知识目录
      │                                    ├─ 重建 index.tsv
      │                                    ├─ 重建 _index.yaml
      │                                    └─ 重建 SUMMARY.md
      │
      └──► 主编本地审核 ──► 拒绝 ──► GitCode 平台拒绝 PR
                                           └─ 附评论说明原因，协作者可修改后重新提交
```

## §5 协作者工作流

```
1. 确认身份
   python3 scripts/ohc-run.py whoami
   → 确认 Agent ID 和角色（contributor）

2. 获取任务（编译某软件）
   → 由主编或任务分配系统指定软件名和版本

3. 同步并创建分支
   git pull origin main
   git checkout -b feat/{software}-{version}
   → 确保基于最新 main 创建分支

4. 执行编译流程（SKILL.md Step 1-5）
   - Step 1: 下载源码
   - Step 2: 检索历史知识
   - Step 2.5: ohc-run.py init-archive → 创建工作目录和 notes.md
   - Step 3: 环境准备 + 编译 + 实时知识提取
   - Step 4: 测试 + 补丁校验
   - Step 5: 归档准备

5. 发现新知识 → 写入草稿
   python3 scripts/ohc-run.py graph add E055 --draft
   → 写入 knowledge/graph/draft/E055-A7F3.yaml
   → 包含 contributor_id: A7F3 字段

6. 本地自检
   python3 scripts/ohc-run.py submit --check <name> <version>
   → 检查：补丁完整性、notes.md 已关闭、manifest.yaml 字段完整
   → 报告通过/失败项

7. 提交并推送到 Git 分支
   git add .
   git commit -m "feat: 编译 {name} {version} - {status}"
   → 包含所有变更：补丁、manifest、notes.md、知识草稿

8. Rebase 并推送
   git rebase main                    # 与 main 同步，解决可能的冲突
   git push origin feat/{software}-{version}

9. 在 GitCode 创建 PR
   → 标题格式：feat: 编译 {软件名} {版本} - {状态}
   → 描述包含三要素：背景、修改、测试
   → 等待主编审核

10. 等待主编审核
   → 主编审核通过 → PR 被 Squash 合并到 main
   → 主编审核拒绝 → 协作者根据评论修改后重新推送并更新 PR
```

## §6 主编工作流

```
1. 确认身份
   python3 scripts/ohc-run.py whoami
   → 确认角色为 editor（OHC_ROLE=editor）

2. 查看 GitCode 待审 PR
   → 在 GitCode 平台上查看所有 Open 状态的 PR
   → 每条显示：PR 标题、软件名、版本、协作者 ID、状态

3. 本地审核 — 获取 PR 分支
   git fetch origin feat/{software}-{version}
   git checkout feat/{software}-{version}
   → 切换到协作者的工作分支

4. 本地审核 — 检查变更
   git diff main...feat/{software}-{version}   # 查看所有变更文件列表
   → 检查提交单详情（manifest.yaml、notes.md）
   → 检查新增知识草稿内容
   → 检查 notes.md 中的知识提取记录
   → 与已有知识进行去重比对
   → 可使用 ohc-run.py review 辅助检查

5. 知识去重和编号统一
   → 检查草稿中的新知识是否与已有条目语义重复
   → 如果有重复，合并或标注
   → 确定最终的编号（可能与草稿中的临时编号不同）

6. 通过 → 平台接受 PR（Squash Merge）
   → 在 GitCode 平台上接受 PR，选择 Squash Merge
   → 本地同步：
     git checkout main
     git pull origin main
   → 执行合并后操作：
     a. 移动知识草稿：knowledge/graph/draft/ → knowledge/graph/ 正式目录
     b. 合并新知识到 knowledge/*.md（如 error-patterns.md）
     c. 重建 knowledge/graph/index.tsv
     d. 重建 knowledge/graph/_index.yaml
     e. 重建 SUMMARY.md
     f. 记录审核日志（含主编 Agent ID）
   → 将重建结果提交到 main：
     git add . && git commit -m "chore: 重建索引 - 合并 {software} {version}"
     git push origin main

7. 或拒绝 → 平台拒绝 PR
   → 在 GitCode 平台上关闭/拒绝 PR
   → 附评论说明具体拒绝原因
   → 草稿文件保留在协作者的分支中，协作者可修改后重新推送并更新 PR
```

## §7 主编审核清单

主编对每个 PR 执行以下检查：

```
□ 补丁完整性：diff 校验通过，每个源码修改都有对应补丁文件
□ PR 格式正确：标题格式符合 feat: 编译 {软件名} {版本} - {状态}
□ 知识无重复：新增的知识条目与已有条目无语义重复
□ manifest.yaml 完整：所有必须字段已填写，test_results 非零值
□ notes.md 已关闭：末尾有"编译结束"时间戳
□ knowledge_ref 正确：manifest.yaml 中的 knowledge_ref 指向实际存在的章节
□ 格式规范：补丁命名（NNNN-description.patch）、manifest.yaml 格式
□ 已执行 ohc-run.py check-knowledge-gap：无遗漏的"⏳ 待评估"条目
□ 临时文件已清理：无 DIAGNOSIS_*.md / MISSING_*.md 等临时文件
□ 知识草稿完整：draft/ 中的草稿文件包含完整的 YAML 字段
□ Agent ID 记录：PR 和草稿中的 contributor_id 与实际 Agent ID 一致
□ 无越权修改：协作者未修改 knowledge/ 正式文件、索引文件或 SUMMARY.md
□ 分支命名规范：分支名符合 feat/{software}-{version} 格式
□ PR 描述完整：包含背景、修改、测试三要素
```

### 审核通过后的操作

主编在 GitCode 平台 Squash 合并 PR 后，本地执行以下操作：

1. `git checkout main && git pull origin main`
2. 移动知识草稿从 `draft/` 到正式目录，合并到 `knowledge/*.md`
3. 重建 `knowledge/graph/index.tsv`
4. 重建 `knowledge/graph/_index.yaml`
5. 重建 `SUMMARY.md`
6. `git add . && git commit -m "chore: 重建索引" && git push origin main`

## §8 并发安全

### 隔离机制

OpenDesk skill 环境中，多个 Agent 实例通过 **Git 分支天然隔离 + 目录隔离 + 角色权限** 保证并发安全，无需额外加锁。

| 资源 | 冲突风险 | 安全机制 |
|------|---------|---------|
| `archives/{letter}/{name}/{version}/` | 🟢 无 | 目录天然隔离——不同软件、不同版本 |
| Git 分支 `feat/{software}-{version}` | 🟢 无 | Git 分支天然隔离——每个协作者在独立分支上工作 |
| `knowledge/graph/draft/` | 🟢 低 | 草稿文件包含 Agent ID 后缀（如 E055-A7F3.yaml），天然隔离 |
| `knowledge/*.md`（正式） | 🟢 无 | 协作者禁止写入，只有主编修改 main 分支 |
| `knowledge/graph/index.tsv` | 🟢 无 | 只有主编写入 |
| `knowledge/graph/_index.yaml` | 🟢 无 | 只有主编写入 |
| `SUMMARY.md` | 🟢 无 | 只有主编写入 |
| `SKILL.md` | 🟢 低 | 很少修改，主编统一管理 |
| `scripts/*.py` | 🟡 中 | 新增脚本需在 PR 中说明 |
| `templates/*.md` | 🟢 低 | 模板稳定后很少变 |

### 为什么不需要编号区间预留

在 Git + PR 工作流中：
- 每个协作者在独立的 `feat/{software}-{version}` 分支上工作，互不干扰
- 协作者将新知识写入 `knowledge/graph/draft/` 的独立 YAML 文件（含 Agent ID 后缀）
- 多个协作者的知识条目在不同分支上，互不冲突
- 主编在合并 PR 时统一编号、去重、合并
- **无需预协商编号区间**，主编拥有最终编号权

## §9 提交规范（GitCode PR 规范）

> 参照 GitCode 多人协作提交规范。所有工作通过 Git 分支和 Pull Request 提交。

### 分支命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能（编译） | `feat/{software}-{version}` | `feat/curl-8.7.1` |
| 修复 | `fix/{description}` | `fix/e055-error-pattern` |
| 优化 | `opt/{description}` | `opt/knowledge-index` |

### PR 标题格式

```
feat: 编译 {软件名} {版本} - {状态}
```

| 状态 | 说明 |
|------|------|
| `success` | 编译成功，测试全部通过 |
| `partial ({通过率}%)` | 编译成功，部分测试失败 |
| `failed` | 编译失败（需附失败原因） |

示例：
```
feat: 编译 curl 8.7.1 - success
feat: 编译 python 3.9.25 - partial (89.4% 测试通过)
fix: 修复 E055 错误模式描述不准确
opt: 优化 knowledge 索引重建流程
```

### PR 描述格式

```markdown
## 背景
{为什么做这个 PR，相关上下文}

## 修改
- {变更项 1}
- {变更项 2}
- ...

## 测试
- {测试方法和结果}
- 本地自检：ohc-run.py submit --check {name} {version} → {通过/失败}
```

### Squash 合并规则

- **默认使用 Squash Merge**：将分支上所有提交压缩为一个，保持 main 历史整洁
- 压缩后的提交消息与 PR 标题一致
- **特殊情况 `[NOSQUASH]`**：如果 PR 包含多个逻辑独立的提交且需要保留完整历史，在 PR 标题前添加 `[NOSQUASH]` 标记，主编将使用普通 Merge

---

# 第二部分：子任务拆分与质量保障

> **本部分面向 AI 自身**，定义在上下文窗口有限时，如何通过子任务拆分保持工作质量。

## 核心问题

上下文窗口有限，长任务必须拆分为子任务。但子任务与父任务之间是**上下文隔离**的——子任务无法读取父任务的对话历史。如果拆分不当，子任务会因缺乏上下文而"降智"，产出质量不可控。

## 子任务拆分三原则

### 原则 1：信息自包含

**每个子任务的 objective 必须包含完成任务所需的全部信息。**

反面教材：
```
❌ objective: "修复审计发现的问题"
   → 子任务不知道有哪些问题、在哪些文件中、具体要改什么
```

正面教材：
```
✅ objective: "修复以下 3 个问题：
   1. 文件 A 第 42 行：把 'bionic' 改为 'musl'
   2. 文件 B §13 标题：E051 → E050
   3. 文件 C 索引表：补充 musl-compat.md 条目
   修复后用 grep 验证每项修改。"
```

### 原则 2：原子性 + 可验证

**子任务应该足够小，使得：(a) 可以完整执行，(b) 输出可以被明确验证。**

- ✅ 好子任务：修改 5 个文件的字段名（明确输入、明确输出）
- ✅ 好子任务：扫描 28 个 manifest.yaml 的 knowledge_gained（有明确的扫描范围和输出格式）
- ❌ 差子任务："优化整个知识库"（范围不清、成功标准模糊）
- ❌ 差子任务："重构 SKILL.md"（会涉及大量上下文，子任务无法独立完成）

### 原则 3：验证在子任务内部

**不要假设子任务会正确执行。每个子任务的 criteria 必须包含自检步骤。**

```
✅ criteria: "修复完成后：(1) grep 确认旧文本已消除 (2) grep 确认新文本已存在 (3) 列出所有修改的文件路径"
❌ criteria: "修复完成"
```

## 何时拆分 vs 何时不拆

### 应该拆分的场景

| 场景 | 原因 | 拆分方式 |
|------|------|---------|
| 多个独立的文件修改 | 每个修改互不依赖 | 按文件分组，每组一个子任务 |
| 大规模扫描/搜索 | 避免大量文件内容污染父上下文 | 一个子任务专门做扫描，返回摘要 |
| 并行独立调研 | 多个方向同时进行 | 每个方向一个子任务，异步执行 |
| 格式化/校验工作 | 机械化但大量 | 单独子任务，带明确规则 |

### 不应该拆分的场景

| 场景 | 原因 |
|------|------|
| 需要跨文件理解全局一致性的修改 | 子任务缺乏全局视图 |
| 创造性设计决策（如流程重构） | 需要充分的上下文和判断 |
| 涉及多个文件的关联修改 | 子任务可能只改了一半 |

### 灰色地带的处理

当不确定是否该拆分时，使用**同步子任务**（isAsync=false）：
- 同步子任务的输出会返回到父任务上下文
- 父任务可以审查结果，决定是否需要修正
- 相当于"把工作委派出去，但自己负责最终质量"

## 上下文传递模式

### 模式 A：全量信息嵌入（推荐用于确定性任务）

将所有需要的信息直接写入 objective：

```
objective: |
  ## 背景
  SKILL.md 的 Phase 1.5 要求创建 notes.md，但 §4 目录结构中遗漏了此文件。

  ## 任务
  在 SKILL.md 的 §4 目录结构中，templates/ 列表里添加 notes.md。

  ## 具体操作
  文件: /path/to/SKILL.md
  找到 "├── manifest.yaml" 这行，在其后添加 "│   ├── notes.md"

  ## 验证
  grep "notes.md" SKILL.md 确认添加成功
```

### 模式 A'：编译任务（⭐ 必须包含文档更新要求）

编译任务的 objective 必须包含以下结构：

```
objective: |
  ## 编译目标
  编译 {软件名} {版本} for HarmonyOS aarch64。
  归档路径: archives/{字母}/{软件名}/{版本}/

  ## 编译步骤
  1. ohc-run.py init-build {软件名} {版本}（下载源码、创建归档骨架）
  2. 应用补丁（如有历史补丁，检查是否需要更新）
  3. configure + make + make install
  4. ohc-run.py conan-init {软件名} {版本}（生成 Conan 配方: conanfile.py + conandata.yml + test_package/）
  5. ohc-run.py conan-verify {软件名} {版本}（8 道门禁验证: G0 预构建 + G1-G4 + L2/L4/L5）

  ## ⭐ 文档更新要求（必须完成）
  ### notes.md 更新
  - configure 完成后：在"对话记录"部分写入：
    - configure 参数（完整命令）
    - 关键发现（如平台检测结果）
  - 编译完成后：更新所有 Phase checkbox 为完成

  ### README.md 更新
  - 补丁应用后：在"补丁说明"部分写入每个补丁用途
  - 问题解决后：在"遇到的问题"部分写入解决方案

  ## 输出要求
  - Conan 配方: conanfile.py + conandata.yml + test_package/ 存在且 conan-verify 通过
  - 归档完整性: manifest.yaml + notes.md + patches/ 都有实际内容
```

- **为什么**：2026-04-24 批量编译发现子任务完成后文档都是骨架模板，无法断点续传。

### 模式 B：探索 + 汇报（推荐用于调研任务）

子任务只负责探索和汇报，不做决策：

```
objective: |
  扫描 archives/ 下所有 manifest.yaml 的 knowledge_gained 字段。
  返回一份列表：哪些条目是跨软件通用的（应该写入 knowledge/ 但当前没有）。
  不需要修改任何文件，只返回分析结果。
```

### 模式 C：流水线（用于串行依赖任务）

子任务 A 的输出作为子任务 B 的输入：

```
父任务:
  1. 创建子任务 A（调研）→ 得到分析报告
  2. 审查报告
  3. 基于报告结论，创建子任务 B（执行修复）
  4. 验证 B 的结果
```

**关键**：父任务必须在 A 和 B 之间做"审查"——不能让 A 的输出直接流入 B。

## 质量保障检查清单

### 子任务创建前

```
□ objective 是否包含了完成任务所需的全部信息？
□ criteria 是否包含了可验证的检查步骤？
□ 子任务的 scope 是否足够小（10 分钟内可完成）？
□ 如果子任务需要读取文件，文件路径是否明确？
□ 如果子任务需要修改文件，修改的具体内容是否明确？
```

### 子任务完成后

```
□ 子任务输出是否满足 criteria 中的每项检查？
□ 修改是否在正确的文件/位置？
□ 是否引入了新的不一致（如格式差异、术语不统一）？
□ 如果使用了异步子任务，是否等待并验证了结果？
```

### 批量子任务编排

```
□ 无依赖的子任务是否设为异步（isAsync=true）并行执行？
□ 有依赖的子任务是否设为同步（isAsync=false）串行执行？
□ 所有子任务完成后，是否做了全局一致性检查？
  （如：子任务 A 修改了文件 X，子任务 B 也修改了文件 X → 可能冲突）
```

## 常见降智模式及预防

| 降智模式 | 表现 | 预防措施 |
|---------|------|---------|
| **信息不足** | 子任务输出偏离预期 | objective 中写入足够的上下文和示例 |
| **过度自由** | 子任务自行发挥，引入不一致 | criteria 中限定修改范围和格式 |
| **幻觉** | 子任务编造不存在的文件/内容 | criteria 中要求 grep 验证 |
| **格式漂移** | 子任务的输出格式与现有内容不一致 | objective 中提供格式示例 |
| **部分完成** | 子任务只完成了一半 | criteria 中列出所有必须完成的项 |

---

# 第三部分：工作流改进规则

> 以下规则来自实际编译任务的失败教训，每一条都有真实案例支撑。

## 💀 流程级致命约束

### D4. Phase 1.5 必须使用 templates/notes.md
> **ohc-run.py init-archive 必须复制 templates/notes.md 并填充变量，禁止在脚本中硬编码模板。**

- **为什么**：历史上存在三套不一致的 notes.md 模板（SKILL.md 内联 / templates/ / ohc-run.py init-archive 硬编码），Phase 编号、字段名、检查点结构各不相同。恢复会话时 AI 读到的格式不可预测。
- **怎么做**：ohc-run.py init-archive 改为 `cp templates/notes.md "${VERSION_DIR}/notes.md"` + sed 替换占位符

### D5. 测试前置准备（Phase 3→4 转换时强制执行）
> **`make check` 前必须完成三个前置步骤。**

1. **预确认弹窗**：`find $PREFIX/bin -type f -executable -exec {} --version \; 2>&1 | head -1`，等待用户确认所有弹窗
2. **禁止并行测试**：`MAKEFLAGS="-j1" make check`（FIFO 限制不仅影响编译，也影响测试套件内部的并行控制）
3. **设置超时**：`timeout 1800 make check`（防止某些测试卡住导致会话超时）

- **为什么**：历史上 coreutils make check 因弹窗未确认大面积误报 Permission denied；cat-self.sh 测试卡住导致会话超时。

### D6. 补丁校验在测试之前执行
> **Phase 4 的正确顺序：补丁校验 → 测试 → 归档。**

- **为什么**：测试可能修改编译目录状态，导致 diff 结果不准确。补丁校验应在对源码的修改最完整、最干净时执行。

### D7. 任务完成度评分卡（四维度）
> **子任务完成标准不仅是"编译成功"，而是四个维度全部达标。**

| 维度 | 量化指标 | 权重 |
|------|---------|------|
| **编译产出** | make install 成功，核心功能验证通过 | 必须 |
| **补丁完整性** | diff 校验通过，每个源码修改都有对应补丁 | 必须 |
| **知识提取** | notes.md 无 ⏳ 待评估条目，HIGH_IMPACT 发现已写入知识草稿 | 必须 |
| **提交完整** | 提交单 YAML 格式正确，所有字段已填写 | 必须 |

- **为什么**：3.9.25 任务在编译产出方面质量很高（80 补丁、89.4% 通过率），但知识提取严重不足、索引未更新、notes.md 未创建。

### D8. Phase 2-4 过程记录（⭐ 新增 2026-04-24）
> **每个子步骤完成后，必须立即更新 notes.md 和 README.md 对应条目。**

| 阶段 | 完成后操作 | 写入位置 |
|------|-----------|----------|
| **configure** | 记录参数、耗时、关键发现 | notes.md 对话记录 |
| **补丁应用** | 记录补丁用途、修改文件 | README.md 补丁说明 |
| **make** | 记录错误、修复方式 | notes.md 对话记录 |
| **make install** | 记录安装路径、文件清单 | notes.md 源码修改清单 |
| **问题解决** | 记录现象、原因、方案 | README.md 遇到的问题 |

- **为什么**：2026-04-24 批量编译发现 32 个归档的 notes.md/README.md 都是骨架模板，编译过程没有自动更新文档的机制，导致无法断点续传、无法复现编译过程。
- **怎么做**：driver.py 在每个 Phase 结束时调用 `update_progress_*()` 函数；子任务 objective 中明确包含文档更新要求。

## 🔴 流程级严重约束

### S4. 知识证伪流程
> **当发现知识库中某条 L1/L2 知识与实际行为矛盾时，必须立即标注 `⚠️ DEPRECATED`。**

- **为什么**：3.9.0 记录了"posix_spawn() 不受 SELinux 限制"，3.9.25 实测所有子进程创建方式均被阻止。
- **怎么做**：在 notes.md 增加"知识证伪"条目；在 knowledge/ 对应位置立即标注 DEPRECATED 并指向正确方案。

### S5. manifest.yaml 自动填充
> **禁止用骨架模板的零值归档。test_results、compile_date 等字段必须用实际数据填充。**

- **为什么**：coreutils manifest 记录 test_results 全为零但实际执行了 707 个测试；compile_date 年份写错为 2024。
- **怎么做**：compile_date 使用 `date +%Y-%m-%d` 自动获取；test_results 从测试日志解析填写。

### S6. 依赖编译作为独立子任务
> **Phase 3 发现缺少依赖时，创建独立子任务编译依赖，主任务等待依赖安装完成。**

- 依赖归档后，在主软件 manifest.yaml 的 `dependencies.required` 中记录归档路径
- 必需依赖编译失败→终止主任务；可选依赖失败→禁用该功能继续编译

### S7. 子任务失败三级响应

| 级别 | 触发条件 | 响应 |
|------|---------|------|
| Level 1 自动重试 | 验证失败 | 用错误信息增强 objective → 重新提交子任务 |
| Level 2 缩小范围 | 重试 2 次仍失败 | 缩小子任务范围或拆分为更小子任务 |
| Level 3 升级 | 范围无法缩小 | 升级为父任务同步执行 |

### S8. 长任务中期盘点
> **编译消息超过 30 条时，强制执行一次中期知识盘点。**

- 使用 `scripts/ohc-run.py check-knowledge-gap` 扫描 notes.md 中的待评估条目
- 目的：防止 76 条消息的长任务中知识遗漏累积到不可收拾

### S9. 临时文件清理（Phase 4 收尾时执行）
> **诊断报告、工作计划等临时文件在价值整合后必须删除。**

- **临时文件前缀**：`DIAGNOSIS_`、`MISSING_`、`WORKFLOW_`、`WORKPLAN_`、`SCAN_`
- **清理命令**：`rm -f DIAGNOSIS_*.md MISSING_*.md WORKFLOW_*.md WORKPLAN_*.md SCAN_*.md`
- **项目根目录只保留**：SKILL.md / KNOW_YOUR_WHY.md / README.md / SUMMARY.md / CONTRIBUTING.md / PREBUILD_TODOLIST.md

### S10. 协作规范（多人 AI 实例并行编译时必须遵守）
> **核心原则：协作者只修改自己负责的归档目录和知识草稿，公共文件由主编在审核批准时统一更新。**

- **目录隔离**：每个 AI 实例只在自己的 `archives/{letter}/{name}/{version}/` 下工作
- **禁止协作者修改**：`knowledge/` 正式文件、`knowledge/graph/index.tsv`、`knowledge/graph/_index.yaml`、`SUMMARY.md`（只由主编在 `approve` 时自动生成）
- **知识写入草稿**：新知识通过 `ohc-run.py graph add E{N} --draft` 写入 `knowledge/graph/draft/`
- **提交单规范**：编译完成后通过 `ohc-run.py submit` 生成提交单，不直接修改公共文件
- **贡献归属**：提交单中的 `contributor_id` 字段标识工作来源，主编审核记录中保留完整归属信息

### S12. 流程自省（最高优先级，贯穿始终）
> **你的双重身份：编译执行者 + 流程质检员。质检员优先级更高。**

- **每次编译都是 SKILL.md 的实战检验**——发现文档问题比完成编译更重要
- **实时记录，不过夜**：发现问题立即写入 `reports/skill-feedback.md`（主编）或 `archives/.../feedback.md`（协作者）
- **Phase 4 额外步骤**：汇总 feedback → 回顾卡壳点 → 写入 manifest.yaml
- **监控 8 类问题**：流程缺失/冲突/冗余、脚本问题、知识导航错误、约束不生效、模板不完整、文档矛盾

### S12.1 保护性约束（防止破坏现有体系）

> **你可能会觉得某些地方可以优化，但不要动手改。你的职责是记录问题，不是修复文档。**

**绝对禁止修改**（违反一次就破坏整个体系）：

- ❌ 不要修改 SKILL.md：章节结构、约束定义、Phase 流程是主编 AI 的职责
- ❌ 不要修改 KNOW_YOUR_WHY.md：约束规则由主编统一维护
- ❌ 不要修改 templates/notes.md 模板：模板已经过 4 轮遗忘曲线优化
- ❌ 不要修改其他软件的档案目录：只修改自己负责的版本目录
- ❌ 不要删除或重命名 knowledge/ 下的知识文件
- ❌ 不要创建临时报告文件（按 S9 规则）

**如果发现需要修改的内容**：
- 文档描述不清楚 → 写入 `archives/.../feedback.md`（协作者）或 `reports/skill-feedback.md`（主编）
- 知识文件内容有误 → 在使用时标注 DEPRECATED，同时写入 feedback
- 模板需要新增内容 → 写入 feedback，标注"建议新增"
- 脚本有 bug → 写入 feedback，标注具体报错和复现步骤

---

# 第四部分：防遗忘策略

> 基于上下文压缩遗忘测试（COMPRESSION_FORGETTING_TEST.md）的结果。

## 遗忘风险数据

| 知识类别 | 遗忘率 | 风险等级 |
|---------|--------|---------|
| 💀 致命级约束 | 57% | 🔴 高 |
| 🔴 严重级约束 | 70% | 🔴 高 |
| 工具脚本列表 | 75% | 🔴 高 |
| 知识文件列表 | 83% | 🔴 高 |
| Phase 转换检查点 | 83% | 🔴 高 |
| 多 Agent 编排规范 | 100% | 🔴 最高 |

## 防遗忘策略

**P0 — 必须立即实施**（防止致命约束遗忘）：

1. **notes.md 内嵌约束速查**：在 notes.md 模板的"编译过程"章节前，嵌入 D1-D7 的速查清单：
   ```markdown
   ## ⚠️ 致命约束速查（不可遗忘）
   - [ ] 补丁完整性：diff -ruN original/ modified/ > all_changes.diff
   - [ ] 提交单自检：ohc-run.py submit --check <name> <version>
   - [ ] 测试前置：弹窗预确认 + MAKEFLAGS=-j1 + timeout 1800
   - [ ] Phase 1.5 不可跳过
   - [ ] 实时知识提取：每次解决问题后判断 L1/L2/L3
   - [ ] 知识证伪：发现与知识库矛盾立即标注 DEPRECATED
   - [ ] 任务完成度：编译+补丁+知识+提交单 四维度
   ```

2. **工具脚本封装确定性操作**：所有"记住一个多步流程然后手动执行"的场景都应该有脚本：
   - `ohc-run.py submit --check` — 封装提交前自检
   - `ohc-run.py submit` — 封装完整的提交单生成
   - `ohc-run.py approve` — 封装主编批准后的所有重建操作
   - 这些脚本即使 AI 遗忘了细节，只需要记住"调用这个命令"

**P1 — 应该尽快实施**（减少效率损失）：

3. **会话恢复包**：ohc-run.py init-archive 在创建骨架时生成"会话恢复包"，包含：
   - 当前编译阶段
   - 已完成的约束检查项
   - 待执行的下一步
   - 这样 AI 在压缩后只需读取恢复包就能知道"我现在在哪、下一步做什么"

4. **知识检索决策树**：SKILL.md 中增加"遇到问题时去哪找"的决策树，避免 AI 需要记住 24 个知识文件的用途

**P2 — 长期优化**：

5. **四维度自动检查**：ohc-run.py close-archive 内嵌四维度自动检查逻辑，输出完成度评分

## "外部记忆"原则

> **AI 不应该记住所有细节，而是记住"去哪里找"和"调用什么工具"。**

- 记住"用 `ci/artifacts/sign.sh`"比记住"GPG 签名 + ELF 签名"容易 100 倍
- 记住"遇到编译错误查 `knowledge/debug-methodology.md`"比记住"编译错误的处理步骤"容易 10 倍
- notes.md 就是 AI 的"外部记忆"——压缩后只需要读取 notes.md 就能恢复上下文

---

*文档版本: 6.0 | Conan 配方体系 + Git+PR 协作模式 | 2026-06-23*
