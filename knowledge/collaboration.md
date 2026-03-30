# 多人 AI 协作开发规范

> 本文档定义了多个 AI 实例协作编译开源软件、提交知识、审核合并的完整工作流程。

## 协作模式

- **纯 AI 协作**：多个 AI 实例同时编译不同的开源软件
- **各自提交 PR**：每个 AI 实例在自己的 Git 分支上工作，编译完成后提交 PR
- **主编 AI 审核**：一个"主编"AI 实例负责审核每个 PR（知识质量、去重、格式规范）

---

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

---

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

---

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
START_NUM=$(printf "E%03d" $((NEXT_NUM + 1)))
END_LABEL=$(printf "E%03d" $END_NUM)

echo "" >> "$FILE"
echo "<!-- RESERVED: ${START_NUM}-${END_LABEL} for ${BRANCH} -->" >> "$FILE"

echo "已预留 $START_NUM-$END_LABEL 给 $BRANCH"
echo "在此分支中，新增的错误编号应从 $START_NUM 开始"
```

### §3.2 知识文件分工

不同类型的知识文件有不同的冲突处理策略：

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

---

## §4 _index.yaml 架构改造

**当前问题**：所有软件的索引条目在一个 _index.yaml 文件中，多人并发追加必然冲突。

**解决方案：拆分为独立 meta 文件 + 聚合脚本**

### §4.1 新增每个软件的 meta 文件

```
archives/p/python/3.9.0/_meta.yaml     # Python 3.9.0 的索引条目
archives/c/curl/8.7.1/_meta.yaml       # curl 8.7.1 的索引条目
```

每个 `_meta.yaml` 内容：

```yaml
software: python
version: 3.9.0
letter: p
status: success           # compiling | success | partial | failed
build_system: autotools
compatibility: medium
patches_count: 11
archive_path: archives/p/python/3.9.0
```

### §4.2 _index.yaml 改为自动聚合

`archives/_index.yaml` 改为**自动生成**文件（类似 SUMMARY.md），由脚本聚合所有 `_meta.yaml`：

```bash
# 聚合脚本
./scripts/aggregate-index.sh
# → 扫描 archives/*/*/*/ _meta.yaml
# → 生成 archives/_index.yaml
# → 生成 SUMMARY.md
```

**规范**：
- 工作分支上只修改 `archives/{letter}/{name}/{version}/_meta.yaml`
- **禁止在工作分支上直接修改 `archives/_index.yaml`**
- `_index.yaml` 只在 main 分支由主编 AI 生成

### §4.3 init-archive.sh / close-archive.sh 适配

- `init-archive.sh`：创建 `_meta.yaml`（status: compiling）而不是修改 `_index.yaml`
- `close-archive.sh`：更新 `_meta.yaml`（status: success/partial/failed）而不是修改 `_index.yaml`
- `_index.yaml` 的生成推迟到 PR 合并时

---

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

---

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

---

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
□ 已执行 check-knowledge-gap.sh：无遗漏的"⏳ 待评估"条目
□ 临时文件已清理：无 DIAGNOSIS_*.md / MISSING_*.md 等临时文件
```

### 审核通过后的操作

1. 合并 PR 到 main
2. 运行 `./scripts/aggregate-index.sh` 更新 `_index.yaml`
3. 运行 `python3 scripts/gen_summary.py` 更新 `SUMMARY.md`
4. 提交 `_index.yaml` 和 `SUMMARY.md` 的更新

---

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
   - Phase 1.5: init-archive.sh → 创建 _meta.yaml
   - Phase 2: 环境准备
   - Phase 3: 编译 + 实时知识提取
   - Phase 4: 测试 + 归档 + close-archive.sh → 更新 _meta.yaml

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
   ./scripts/aggregate-index.sh
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

## §9 遗忘曲线与防遗忘策略

> 基于上下文压缩遗忘测试（COMPRESSION_FORGETTING_TEST.md）的结果。

### §9.1 遗忘风险数据

| 知识类别 | 遗忘率 | 风险等级 |
|---------|--------|---------|
| 💀 致命级约束 | 57% | 🔴 高 |
| 🔴 严重级约束 | 70% | 🔴 高 |
| 工具脚本列表 | 75% | 🔴 高 |
| 知识文件列表 | 83% | 🔴 高 |
| Phase 转换检查点 | 83% | 🔴 高 |
| 多 Agent 编排规范 | 100% | 🔴 最高 |

### §9.2 防遗忘策略

**P0 — 必须立即实施**（防止致命约束遗忘）：

1. **PROGRESS.md 内嵌约束速查**：在 PROGRESS.md 模板的"编译过程"章节前，嵌入 D1-D7 的速查清单：
   ```markdown
   ## ⚠️ 致命约束速查（不可遗忘）
   - [ ] 补丁完整性：diff -ruN original/ modified/ > all_changes.diff
   - [ ] 索引同步：init-archive.sh 创建 _meta.yaml（不修改 _index.yaml）
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

3. **会话恢复包**：init-archive.sh 在创建骨架时生成"会话恢复包"，包含：
   - 当前编译阶段
   - 已完成的约束检查项
   - 待执行的下一步
   - 这样 AI 在压缩后只需读取恢复包就能知道"我现在在哪、下一步做什么"

4. **知识检索决策树**：SKILL.md 中增加"遇到问题时去哪找"的决策树，避免 AI 需要记住 24 个知识文件的用途

**P2 — 长期优化**：

5. **四维度自动检查**：close-archive.sh 内嵌四维度自动检查逻辑，输出完成度评分

### §9.3 "外部记忆"原则

> **AI 不应该记住所有细节，而是记住"去哪里找"和"调用什么工具"。**

- 记住"用 `./scripts/sign-elf.sh`"比记住"先 llvm-objcopy --remove-section .codesign 再 binary-sign-tool 再 chmod"容易 100 倍
- 记住"遇到编译错误查 `knowledge/debug-methodology.md`"比记住"编译错误的处理步骤"容易 10 倍
- PROGRESS.md 就是 AI 的"外部记忆"——压缩后只需要读取 PROGRESS.md 就能恢复上下文

---

*文档版本: 1.1*
*最后更新: 2026-03-30*
*新增: §8 Agent 分支工作流、§9 遗忘曲线与防遗忘策略*
