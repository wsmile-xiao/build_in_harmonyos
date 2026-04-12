# 多 Agent 协作与任务编排规范

> **用途**: 定义多 Agent 实例协作编译、子任务拆分、审核合并的完整工作流，以及从历史执行中提炼的流程改进规则。
> **覆盖范围**: 协作架构、分支规范、子任务拆分原则、质量保障、工作流改进规则、防遗忘策略。

---

# 第一部分：协作架构与工作流

> 本部分定义了多个 AI 实例协作编译开源软件、提交知识、审核合并的完整工作流。

## 协作模式

- **纯 AI 协作**：多个 AI 实例同时编译不同的开源软件
- **各自提交 PR**：每个 AI 实例在自己的 Git 分支上工作，编译完成后提交 PR
- **主编 AI 审核**：一个"主编"AI 实例负责审核每个 PR（知识质量、去重、格式规范）

## §1 协作架构概述

```
AI 实例 A (编译 curl)     AI 实例 B (编译 nginx)     AI 实例 C (编译 redis)
     │                         │                         │
     ├─ git checkout -b feature/curl-8.7.1
     ├─ Phase 0-4 编译
     ├─ git add + commit
     ├─ git push origin feature/curl-8.7.1
     └─ 创建 PR ────────┐
                       │
     ├─ git checkout -b feature/nginx-1.25
     ├─ Phase 0-4 编译
     ├─ git add + commit
     ├─ git push origin feature/nginx-1.25
     └─ 创建 PR ──────┤
                     │
     ├─ git checkout -b feature/redis-7.2
     ├─ Phase 0-4 编译
     ├─ git add + commit
     ├─ git push origin feature/redis-7.2
     └─ 创建 PR ───┐
                   │
                   ▼
            ┌──────────────┐
            │  主编 AI 审核  │
            │  - 知识去重    │
            │  - 编号修正    │
            │  - 格式校验    │
            │  - 冲突解决    │
            └──────┬───────┘
                   │
                   ▼
            merge to main
                   │
                   ▼
            gen_summary.py
            生成 SUMMARY.md
```

## §2 分支命名规范

```
feature/{软件名}-{版本}

示例：
  feature/curl-8.7.1
  feature/python-3.9.25
  feature/openssl-3.0
  feature/knowledge-fix-E055    # 纯知识修复分支
```

分支从 main 最新提交创建。每个分支只负责一个软件的编译归档。

## §3 知识文件并发冲突解决方案

**核心问题**：多个 AI 同时往 error-patterns.md / harmonyos-specifics.md 等文件追加内容，导致 Git merge 冲突。

**解决方案：编号区间预留 + 分支隔离 + 主编去重**

### §3.1 编号区间分配

error-patterns.md 的错误编号（E0xx）分配规则：

```
当前 main 分支最大编号：E054

AI 实例 A 在创建分支时：
  → 预留 E055-E069（15 个编号）
  → 在分支的 error-patterns.md 中从 E055 开始编号

AI 实例 B 在创建分支时（稍后创建）：
  → 预留 E070-E084（15 个编号）
  → 在分支的 error-patterns.md 中从 E070 开始编号

预留方式：在分支创建时，在 error-patterns.md 末尾追加注释：
  <!-- RESERVED: E055-E069 for feature/curl-8.7.1 -->
  <!-- RESERVED: E070-E084 for feature/nginx-1.25 -->
```

**预留脚本**（AI 在分支创建时执行）：

```bash
#!/bin/sh
# reserve-range.sh <分支名>
# 用法：./scripts/reserve-range.sh feature/curl-8.7.1

BRANCH="$1"
FILE="knowledge/error-patterns.md"
NEXT_NUM=$(grep -oP 'E\d+' "$FILE" | tail -1 | grep -oP '\d+' | sed 's/^0*//')
END_NUM=$((NEXT_NUM + 14))
START_NUM=$(printf "E%03d" $((NEXT_NUM + 1))))
END_LABEL=$(printf "E%03d" $END_NUM)

echo "" >> "$FILE"
echo "<!-- RESERVED: ${START_NUM}-${END_LABEL} for ${BRANCH} -->" >> "$FILE"

echo "已预留 $START_NUM-$END_LABEL 给 $BRANCH"
echo "在此分支中，新增的错误编号应从 $START_NUM 开始"
```

### §3.2 知识文件冲突风险矩阵

| 知识文件 | 冲突风险 | 处理策略 |
|---------|---------|---------|
| error-patterns.md | 🔴 高（频繁追加） | 编号区间预留 + 主编合并去重 |
| harmonyos-specifics.md | 🟡 中（章节内追加） | 按章节分工，主编合并 |
| build-systems.md | 🟡 中 | 同上 |
| musl-compat.md | 🟢 低（很少修改） | 正常 Git merge |
| best-practices.md | 🟢 低 | 正常 Git merge |
| troubleshooting.md | 🟡 中 | 编号区间预留 |

### §3.3 主编合并流程

主编 AI 收到 PR 后的审核步骤：

1. **冲突检测**：检查 PR 与 main 的 diff，识别是否有 merge 冲突
2. **编号重映射**：如果多个 PR 预留了不同区间，合并后主编统一重新编号
3. **知识去重**：检查新增知识是否与 main 已有条目重复（语义级别去重，不只看字面）
4. **格式校验**：检查 Markdown 格式、manifest.yaml 字段完整性
5. **交叉引用更新**：检查 manifest.yaml 的 knowledge_ref 是否指向正确的 knowledge/ 文件和编号
6. **SUMMARY.md 重新生成**：所有 PR 合并后，运行 gen_summary.py

## ⚠️ §4 索引架构（过时 — 仅供参考）

> ⚠️ **过时提示**：本节描述的 `_meta.yaml` / `_index.yaml` 架构已被 `manifest.yaml` 体系取代。当前各软件的索引信息已通过 `manifest.yaml` 统一管理，`aggregate-index.sh` 和 `_index.yaml` 不再使用。以下内容保留供历史参考。

### §4.1 原始方案：拆分为独立 meta 文件 + 聚合脚本

原设计为每个软件新增 `_meta.yaml`：

```
archives/p/python/3.9.0/_meta.yaml     # Python 3.9.0 的索引条目
archives/c/curl/8.7.1/_meta.yaml       # curl 8.7.1 的索引条目
```

`archives/_index.yaml` 原为自动聚合文件，由脚本扫描所有 `_meta.yaml` 生成。

**原规范**（已不再适用）：
- 工作分支上只修改 `archives/{letter}/{name}/{version}/_meta.yaml`
- **禁止在工作分支上直接修改 `archives/_index.yaml`**
- `_index.yaml` 只在 main 分支由主编 AI 生成

### §4.2 当前替代方案

当前使用 `manifest.yaml` 作为每个软件的唯一元数据文件，索引信息从 manifest.yaml 中聚合。脚本 `gen_summary.py` 负责从 manifest.yaml 生成 `SUMMARY.md`。

## §5 PROGRESS.md 与会话恢复（多实例）

**问题**：多个 AI 实例同时编译不同软件，每个实例需要独立恢复自己的进度。

**解决方案**：PROGRESS.md 已在每个软件的 archive 目录下（Phase 1.5 创建），天然隔离。恢复流程：

```bash
# AI 实例启动时，扫描自己负责的软件的 PROGRESS.md
# 而不是扫描所有 status: compiling 的条目

# 恢复命令
cat archives/c/curl/8.7.1/PROGRESS.md
```

**关键**：不要用 `_index.yaml status: compiling` 来发现进行中的编译（多实例会互相干扰），而是直接读取特定软件的 PROGRESS.md。

## §6 PR 提交规范

### PR 标题格式

```
[编译] {软件名} {版本} - {状态}
[编译] curl 8.7.1 - success
[编译] python 3.9.25 - partial (89.4% 测试通过)
[知识] 修复 E055 错误模式描述不准确
```

### PR 描述模板

```markdown
## 编译信息
- 软件：{name}
- 版本：{version}
- 构建系统：{build_system}
- 状态：{status}

## 新增知识
- error-patterns.md: E055-E060（6 条新错误模式）
- harmonyos-specifics.md: §19（新增 lseek 限制）

## 补丁列表
| # | 补丁文件名 | 作用 |
|---|-----------|------|
| 0001 | config.guess-harmonyos.patch | 平台识别 |
| 0002 | fix-musl-compat.patch | musl 兼容性 |

## 测试结果
- 类型：official
- 通过：29 / 失败：6
- 失败原因：SELinux 软链接限制（非功能问题）

## 冲突说明
- 本 PR 预留了 E055-E069 编号区间
- 修改了 archives/c/curl/8.7.1/_meta.yaml（新增，不修改 _index.yaml）
```

## §7 主编 AI 审核清单

主编 AI 对每个 PR 执行以下检查：

```
□ 补丁完整性：diff 校验通过，每个源码修改都有对应补丁
□ 编号无冲突：预留区间未与其他 PR 重叠
□ 知识无重复：新增的 E0xx 与 main 分支已有的条目无语义重复
□ manifest.yaml 完整：所有必须字段已填写，test_results 非零
□ _meta.yaml 已创建：status 正确
□ 未直接修改 _index.yaml：确认 _index.yaml 无变更
□ 未直接修改 SUMMARY.md：确认 SUMMARY.md 无变更
□ PROGRESS.md 已关闭：末尾有"编译结束"时间戳
□ knowledge_ref 正确：manifest.yaml 中的 knowledge_ref 指向实际存在的章节
□ 格式规范：补丁命名（NNNN-description.patch）、manifest.yaml 格式
□ 已执行 ohc-run.py check-knowledge-gap：无遗漏的"⏳ 待评估"条目
□ 临时文件已清理：无 DIAGNOSIS_*.md / MISSING_*.md 等临时文件
```

### 审核通过后的操作

1. 合并 PR 到 main
3. 运行 `python3 scripts/gen_summary.py` 更新 `SUMMARY.md`
4. 提交索引和总览的更新

## §8 Agent 分支工作流（完整生命周期）

### §8.1 角色

| 角色 | 职责 | Git 身份 | 数量 |
|------|------|---------|------|
| **贡献者 Agent** | 编译软件、编写补丁、提取知识、提交 PR | `Author: contributor-{id}` | 多个 |
| **主编 Agent** | 审核 PR、解决冲突、校验知识、合并到 main | `Author: editor` `Committer: editor` | 1 个 |

**区分方式**：
- **贡献者**：创建 feature 分支并提交 commit 的人。在 Git 中通过 `Author` 字段标识。
- **主编**：审核 PR 并执行 merge 的人。在 Git 中通过 merge commit 的 `Author` 字段标识。
- **区分时机**：在 PR 创建阶段就已经区分了——创建 PR 的人就是贡献者，处理 PR 的人就是主编。

### §8.2 贡献者 Agent 工作流

```
1. 拉取仓库
   git clone <repo-url> <skill-dir>
   cd <skill-dir>
   git checkout main && git pull

2. 创建工作分支
   git checkout -b feature/{软件名}-{版本}

3. 预留知识编号区间
   ./scripts/reserve-range.sh feature/{软件名}-{版本}
   → 输出: "已预留 E055-E069"

4. 执行编译流程 (Phase 0 → 4)
   - Phase 0: 下载源码
   - Phase 1: 检索历史知识
   - Phase 1.5: ohc-run.py init-archive → 创建 _meta.yaml
   - Phase 2: 环境准备
   - Phase 3: 编译 + 实时知识提取
   - Phase 4: 测试 + 归档 + ohc-run.py close-archive → 更新 _meta.yaml

5. 提交到自己的分支
   git add archives/{letter}/{name}/{version}/
   git add knowledge/
   git add scripts/ (如有新增)
   git commit -m "[编译] {软件名} {版本} - {status}

   - 补丁: {N} 个
   - 新增知识: E{xxx}-E{yyy}
   - 测试: {passed}/{total}

   编译环境: HarmonyOS {kernel_version} aarch64
   Agent: contributor-{id}"

   git push origin feature/{软件名}-{版本}

6. 创建 PR (通过 GitCode API 或 CLI)
   标题: [编译] {软件名} {版本} - {status}
   描述: 按 §6 模板填写
```

### §8.3 主编 Agent 工作流

```
1. 接收 PR 通知
   → 获取 PR 信息：分支名、提交者、变更文件列表、diff

2. 本地合并（保留贡献者信息）
   git fetch origin feature/{软件名}-{版本}
   git checkout main && git pull
   git merge --no-ff feature/{软件名}-{版本} \
     -m "Merge PR #{N}: [编译] {软件名} {版本}

   Contributed-by: contributor-{id} <agent-{id}@opendesk>
   Reviewed-By: editor <editor@opendesk>"

   ⚠️ 关键：使用 git merge --no-ff 而不是 git am / 手动应用 patch
   这样贡献者的 commit 历史完整保留

3. 如果有冲突，解决冲突
   # 查看冲突文件
   git diff --name-only --diff-filter=U
   
   # 手动解决冲突后
   git add <resolved-files>
   git commit --no-edit  # 保留 merge commit message
   
   ⚠️ 冲突解决原则：
   - knowledge/*.md: 保留双方的条目，主编负责去重和重新编号
   - _index.yaml: 不应出现在冲突中（工作分支不应修改）
   - SUMMARY.md: 不应出现在冲突中

4. 审核（按 §7 审核清单）
   □ 所有 12 项检查通过

5. 重新生成索引
   python3 scripts/gen_summary.py
   git add archives/_index.yaml SUMMARY.md
   git commit -m "chore: 更新索引和总览 (PR #{N})"

6. 推送到 main
   git push origin main

7. 关闭 PR
   在 GitCode 上关闭 PR，添加审核评论
```

### §8.4 Git 贡献归属详解

**核心原则：使用 `git merge` 而不是 `git am` 或手动应用 patch。**

```
提交者 Agent 的 commit:
┌──────────────────────────────────────────────────┐
│ commit abc1234                                    │
│ Author: contributor-A <agent-a@opendesk>  ← 提交者│
│ Date:   2026-03-30 14:00                          │
│                                                  │
│     [编译] curl 8.7.1 - success                    │
│     补丁: 3 个, 新增知识: E055-E058               │
└──────────────────────────────────────────────────┘
                      │
                      ▼ git merge --no-ff
                      │
主编 Agent 的 merge commit:
┌──────────────────────────────────────────────────┐
│ commit def5678 (HEAD -> main)                     │
│ Author: editor <editor@opendesk>           ← 主编 │
│ Merge: xyz..abc                                    │
│ Date:   2026-03-30 14:30                          │
│                                                  │
│     Merge PR #42: [编译] curl 8.7.1               │
│     Contributed-by: contributor-A ...              │
│     Reviewed-By: editor ...                        │
└──────────────────────────────────────────────────┘
```

**查看贡献归属**：
```bash
# 查看某个贡献者的所有提交
git log --author="contributor-A"

# 查看主编合并了哪些 PR
git log --author="editor" --merges

# 查看完整贡献统计
git shortlog -sn --all

# PR 页面上也会显示贡献者信息和合并者信息
```

**为什么不用 `git am` / 手动应用 patch**：
- `git am` 会把所有 commit 变成主编的 commit，原始 Author 丢失
- 手动应用 patch 同上
- `git merge --no-ff` 完整保留双方的历史，是 Git 社区的标准做法

### §8.5 Skill 目录管理

每个 Agent 实例的本地 skill 目录结构：

```
<agent-home>/
└── build_in_harmonyos/     # git clone 到这里
    ├── SKILL.md
    ├── KNOW_YOUR_WHY.md
    ├── knowledge/
    ├── archives/
    ├── scripts/
    └── templates/
```

**关键规范**：
- Agent 启动时 `git clone` 或 `git pull` 获取最新代码
- 编译过程中所有文件变更都在这个目录内
- Phase 4 完成后，只 commit 自己负责的文件
- **不要 commit 临时文件**（遵循 S9 清理规则）
- **不要 commit 自动生成的文件**（_index.yaml、SUMMARY.md）

### §8.6 多 Agent 并发安全矩阵

| 资源 | 冲突风险 | 安全机制 |
|------|---------|---------|
| `archives/{letter}/{name}/{version}/` | 🟢 无（不同软件） | 目录天然隔离 |
| `knowledge/error-patterns.md` | 🔴 高 | 编号区间预留 |
| `knowledge/harmonyos-specifics.md` | 🟡 中 | 按章节分工 |
| `knowledge/build-systems.md` | 🟡 中 | 按章节分工 |
| `archives/_index.yaml` | 🔴 高 | 禁止工作分支修改 |
| `SUMMARY.md` | 🔴 高 | 禁止工作分支修改 |
| `SKILL.md` | 🟢 低（很少修改） | 主编统一管理 |
| `scripts/*.sh` | 🟡 中 | 新增脚本需 PR 说明 |
| `templates/*.md` | 🟢 低 | 模板稳定后很少变 |

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
  SKILL.md 的 Phase 1.5 要求创建 PROGRESS.md，但 §4 目录结构中遗漏了此文件。

  ## 任务
  在 SKILL.md 的 §4 目录结构中，templates/ 列表里添加 PROGRESS.md。

  ## 具体操作
  文件: /path/to/SKILL.md
  找到 "├── manifest.yaml" 这行，在其后添加 "│   ├── PROGRESS.md"

  ## 验证
  grep "PROGRESS.md" SKILL.md 确认添加成功
```

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

### D4. Phase 1.5 必须使用 templates/PROGRESS.md
> **ohc-run.py init-archive 必须复制 templates/PROGRESS.md 并填充变量，禁止在脚本中硬编码模板。**

- **为什么**：历史上存在三套不一致的 PROGRESS.md 模板（SKILL.md 内联 / templates/ / ohc-run.py init-archive 硬编码），Phase 编号、字段名、检查点结构各不相同。恢复会话时 AI 读到的格式不可预测。
- **怎么做**：ohc-run.py init-archive 改为 `cp templates/PROGRESS.md "${VERSION_DIR}/PROGRESS.md"` + sed 替换占位符

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
| **知识提取** | PROGRESS.md 无 ⏳ 待评估条目，HIGH_IMPACT 发现已写入 knowledge/ | 必须 |
| **索引同步** | _index.yaml 包含新版本，gen_summary.py 已执行 | 必须 |

- **为什么**：3.9.25 任务在编译产出方面质量很高（80 补丁、89.4% 通过率），但知识提取严重不足、索引未更新、PROGRESS.md 未创建。

## 🔴 流程级严重约束

### S4. 知识证伪流程
> **当发现知识库中某条 L1/L2 知识与实际行为矛盾时，必须立即标注 `⚠️ DEPRECATED`。**

- **为什么**：3.9.0 记录了"posix_spawn() 不受 SELinux 限制"，3.9.25 实测所有子进程创建方式均被阻止。
- **怎么做**：在 PROGRESS.md 增加"知识证伪"条目；在 knowledge/ 对应位置立即标注 DEPRECATED 并指向正确方案。

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

- 使用 `scripts/ohc-run.py check-knowledge-gap` 扫描 PROGRESS.md 中的待评估条目
- 目的：防止 76 条消息的长任务中知识遗漏累积到不可收拾

### S9. 临时文件清理（Phase 4 收尾时执行）
> **诊断报告、工作计划等临时文件在价值整合后必须删除。**

- **临时文件前缀**：`DIAGNOSIS_`、`MISSING_`、`WORKFLOW_`、`WORKPLAN_`、`SCAN_`
- **清理命令**：`rm -f DIAGNOSIS_*.md MISSING_*.md WORKFLOW_*.md WORKPLAN_*.md SCAN_*.md`
- **项目根目录只保留**：SKILL.md / KNOW_YOUR_WHY.md / README.md / SUMMARY.md / CONTRIBUTING.md / PREBUILD_TODOLIST.md

### S10. 协作规范（多人 AI 实例并行编译时必须遵守）
> **核心原则：工作分支只修改自己负责的文件，公共文件由主编 AI 在合并时生成。**

- **分支隔离**：每个 AI 实例在自己的 `feature/{软件名}-{版本}` 分支上工作
- **禁止在分支上修改**：`archives/_index.yaml`、`SUMMARY.md`（只在 main 分支由主编生成）
- **索引用 _meta.yaml**：每个软件的索引信息存在 `archives/{letter}/{name}/{version}/_meta.yaml`
- **知识编号预留**：error-patterns.md 的 E0xx 编号在分支创建时预留区间
- **贡献归属**：使用 `git merge --no-ff` 合并 PR，保留 commit 历史

### S12. 流程自省（最高优先级，贯穿始终）
> **你的双重身份：编译执行者 + 流程质检员。质检员优先级更高。**

- **每次编译都是 SKILL.md 的实战检验**——发现文档问题比完成编译更重要
- **实时记录，不过夜**：发现问题立即写入 `reports/skill-feedback.md`
- **Phase 4 额外步骤**：汇总 feedback → 回顾卡壳点 → 写入 manifest.yaml
- **监控 8 类问题**：流程缺失/冲突/冗余、脚本问题、知识导航错误、约束不生效、模板不完整、文档矛盾

### S12.1 保护性约束（防止破坏现有体系）

> **你可能会觉得某些地方可以优化，但不要动手改。你的职责是记录问题，不是修复文档。**

**绝对禁止修改**（违反一次就破坏整个体系）：

- ❌ 不要修改 SKILL.md：章节结构、约束定义、Phase 流程是主编 AI 的职责
- ❌ 不要修改 KNOW_YOUR_WHY.md：约束规则由主编统一维护
- ❌ 不要修改 templates/PROGRESS.md 模板：模板已经过 4 轮遗忘曲线优化
- ❌ 不要修改其他软件的档案目录：只修改自己负责的版本目录
- ❌ 不要删除或重命名 knowledge/ 下的知识文件
- ❌ 不要创建临时报告文件（按 S9 规则）

**如果发现需要修改的内容**：
- 文档描述不清楚 → 写入 `reports/skill-feedback.md`
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

1. **PROGRESS.md 内嵌约束速查**：在 PROGRESS.md 模板的"编译过程"章节前，嵌入 D1-D7 的速查清单：
   ```markdown
   ## ⚠️ 致命约束速查（不可遗忘）
   - [ ] 补丁完整性：diff -ruN original/ modified/ > all_changes.diff
   - [ ] 索引同步：ohc-run.py init-archive 创建 _meta.yaml（不修改 _index.yaml）
   - [ ] 测试前置：弹窗预确认 + MAKEFLAGS=-j1 + timeout 1800
   - [ ] Phase 1.5 不可跳过
   - [ ] 实时知识提取：每次解决问题后判断 L1/L2/L3
   - [ ] 知识证伪：发现与知识库矛盾立即标注 DEPRECATED
   - [ ] 任务完成度：编译+补丁+知识+索引 四维度
   ```

2. **工具脚本封装确定性操作**：所有"记住一个多步流程然后手动执行"的场景都应该有脚本：
   - `prep-test.sh` — 封装测试前置三步（弹窗+j1+timeout）
   - `full-archive.sh` — 封装完整的归档收尾流程
   - 这些脚本即使 AI 遗忘了细节，只需要记住"调用这个脚本"

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

- 记住"用 `./scripts/ohc-run.py sign-elf`"比记住"先 llvm-objcopy --remove-section .codesign 再 binary-sign-tool 再 chmod"容易 100 倍
- 记住"遇到编译错误查 `knowledge/debug-methodology.md`"比记住"编译错误的处理步骤"容易 10 倍
- PROGRESS.md 就是 AI 的"外部记忆"——压缩后只需要读取 PROGRESS.md 就能恢复上下文

---

*文档版本: 3.0 | 合并自 collaboration.md v1.1 + collaboration-guidelines.md v2.3*
*最后更新: 2026-04-11*
