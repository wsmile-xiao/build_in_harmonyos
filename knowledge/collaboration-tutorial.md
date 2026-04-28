# 协作提交教程

> 从入门到主编：在 OpenHarmony Compile Agent 中使用 Git + GitCode PR 工作流协作
> 参照 GitCode 多人协作规范，标准 Squash + 半线性合并配置

---

## 一、核心概念

本项目采用 **Git + GitCode PR** 工作流。协作者在本地分支上编译、提交改动，最终通过 GitCode 平台发起 Pull Request，由主编审核合并。

### Git+PR vs 旧版提交单对比

| 旧版提交单概念 | Git+PR 等价物 | 说明 |
|----------------|--------------|------|
| 协作者的 archive 目录 | Git 功能分支 `feat/<软件名>` | 每人一个分支，天然隔离 |
| 提交单 (`submissions/pending/`) | GitCode Pull Request | 协作者发起 PR，主编在平台上审核 |
| 主编 `approve` | GitCode 平台 Merge PR | Squash 合并（默认），半线性 |
| 主编 `reject` | GitCode 平台 Close PR | 附拒绝原因，协作者修改后重发 PR |
| 主编 `review`（12 项检查） | `submit --check` + 本地 `git diff` 审核 | 协作者先自检，主编再做完整审核 |
| `approve` 后自动重建索引 | 合并后主编本地 `git pull` + 重建索引 | 索引重建仍在本地执行 |

### 关键文件分区

```
项目根目录/
├── archives/              ← 贡献区（协作者各自负责的软件）
├── knowledge/graph/       ← 共享知识区
│   └── draft/             ← 协作者的草稿（随分支提交）
├── scripts/               ← 脚本（主编可改）
├── reports/               ← 反馈渠道
├── templates/             ← 模板（主编可改）
├── references/            ← 参考资料（主编可改）
└── submissions/           ← 提交单存档（已废弃，保留供历史查阅）
```

> **核心原则**：协作者的改动（`archives/` 和 `knowledge/graph/draft/`）通过 Git 分支提交，不直接操作 `main` 分支。所有合并走 GitCode PR。

---

## 二、协作者提交全流程（5 步）

### 步骤 1：领取任务，创建分支

```bash
# 1. 设置 Agent ID（4 位十六进制，会话内固定）
export OHC_AGENT_ID="A7F3"

# 2. 同步最新 main
git pull origin main

# 3. 创建功能分支（分支命名见 §四）
git checkout -b feat/wget-1.21
```

> **分支命名规则**（参照 GitCode 规范）：
> - `feat/<软件名>-<版本>` — 新软件编译（如 `feat/wget-1.21`）
> - `fix/<软件名>-<问题>` — 修复已有编译问题
> - `opt/<软件名>-<优化内容>` — 编译优化
> - `refactor/<内容>` — 重构
> - `docs/<内容>` — 文档更新
> - `chore/<内容>` — 杂项

### 步骤 2：编译、调试、自由迭代

开发过程中自由工作，每完成一个阶段即可 commit，不需要刻意整理提交信息：

```bash
# 初始化（自动检查依赖、下载、解压）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build wget 1.21

# 编译过程中可能遇到问题
# → 查知识图谱 / 改 config.guess / 加补丁
# → 自由迭代，阶段性地 git commit

# 阶段性提交示例（提交信息随意，最终会 Squash）
git add archives/w/wget/1.21/
git commit -m "wget 1.21: 编译进行中，补丁调试中"

# 质量门禁
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build wget 1.21

# 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish wget 1.21 success
```

> **Squash 合并保证整洁**：PR 合并时会将分支上的所有 commit 压缩为一个，所以协作者在分支上可以随意 commit，无需规范提交信息。

### 步骤 3：提交前整理（关键步骤）

提交前确保归档目录干净、完整，并写入知识草稿：

```bash
# 确认 notes.md 已关闭
grep "status:" archives/w/wget/1.21/notes.md
# 应输出: status: success（或 partial）

# 确认 manifest.yaml 完整
cat archives/w/wget/1.21/manifest.yaml

# 添加知识图谱草稿（如有新经验）
python3 $SKILL_ROOT/scripts/ohc-run.py graph add --draft \
  --title "E082: wget 链接阶段找不到 openssl" \
  --error-pattern "undefined reference to SSL_" \
  --solution "configure 时加 --with-ssl=$DEFAULT_PREFIX" \
  --match-keywords "wget,openssl,SSL,undefined reference"

# 自检（12 项自动检查，本地验证）
python3 $SKILL_ROOT/scripts/ohc-run.py submit --check wget 1.21
```

**12 项自检清单**（`submit --check` 自动执行）：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | 补丁完整性 | 每个 `.patch` 文件格式合法、命名规范 |
| 2 | E 编号冲突 | 新增知识编号不与已有编号冲突 |
| 3 | 知识去重 | 草稿关键词不与已有条目严重重复 |
| 4 | Manifest 完整性 | 必填字段齐全，test_results 非全零 |
| 5 | 禁止文件检查 | 未修改 `_index.yaml`、`SUMMARY.md` 等 |
| 6 | notes.md 关闭 | `notes.md` 包含结束标记 |
| 7 | 临时文件 | 无 `DIAGNOSIS_*`、`MISSING_*` 等临时文件 |
| 8 | knowledge_ref 引用 | manifest 中引用的知识文件均存在 |
| 9 | 打包产物 | `packaging/` 下有 `tar.gz`（success/partial 时） |
| 10 | 测试报告 | `reports/test-report.md` 存在 |
| 11 | 提交自检 | 以上各项综合评估 |
| 12 | 总体评估 | PASS / WARN / FAIL 汇总 |

> **自检通过后**才能继续提交。自检是本地验证，不涉及远程仓库。

### 步骤 4：提交到 Git 分支

整理完成后，将改动 commit 到功能分支：

```bash
# 添加所有改动（archives/ 和 knowledge/graph/draft/）
git add archives/w/wget/1.21/
git add knowledge/graph/draft/

# 提交（信息简洁即可，Squash 合并时会用 PR 标题替代）
git commit -m "feat(wget): 编译 wget 1.21 完成"

# Rebase 到最新 main（半线性合并要求）
git fetch origin
git rebase origin/main

# 推送到远程
git push origin feat/wget-1.21
```

> **为什么必须 rebase**：GitCode 半线性合并配置要求分支的最新 commit 必须基于 main 的最新 HEAD。不 rebase 会导致 PR 无法合并。

### 步骤 5：在 GitCode 上创建 PR

推送到远程后，在 GitCode 平台上创建 Pull Request：

**PR 标题格式**（参照 GitCode 规范）：

```
类型: 一句话描述（50 字内）
```

示例：
```
feat: 编译 wget 1.21 成功，含 3 个补丁和 2 条知识草稿
fix: 修复 curl 8.7.1 musl 兼容性问题
opt: 优化 nginx 1.25 编译参数，体积减少 12%
```

**PR 描述三要素**（参照 GitCode 规范）：

```markdown
## 背景
编译 wget 1.21，用于 OpenHarmony 预编译包仓库。wget 是基础网络工具，
属于 core-network 依赖树。

## 修改
- 新增 archives/w/wget/1.21/ 完整归档
- 新增 3 个补丁：0001-config.guess-harmonyos.patch、0002-fix-musl-compat.patch、0003-disable-ipv6-tests.patch
- 新增 2 条知识草稿：E082（openssl 链接）、E083（musl getconf）
- 测试结果：29 passed / 6 failed（SELinux 软链接限制，非功能问题）

## 测试
- ✅ submit --check 12 项全部 PASS
- ✅ verify-build 通过
- ✅ 本地功能验证：wget --version 正常输出
```

> **特殊情况 [NOSQUASH]**：如果分支上的提交历史有独立价值（如多个独立修复），可在 PR 标题中加 `[NOSQUASH]` 前缀，主编将以普通 merge 方式合并，保留完整提交历史。一般情况不需要。

---

## 三、主编审核全流程（4 步）

### 步骤 1：查看 PR 列表

在 GitCode 平台上查看待审核 PR 列表，或本地查看：

```bash
export OHC_ROLE=editor

# 查看所有待审核 PR 对应的远程分支
git fetch origin
git branch -r | grep -E 'origin/(feat|fix|opt|refactor|docs|chore)/'

# 也可以用 submission 工具辅助（如果协作者同时生成了提交单）
python3 $SKILL_ROOT/scripts/ohc-run.py review --list
```

### 步骤 2：本地审核变更

主编在本地 fetch 分支，逐项审核变更：

```bash
# fetch 协作者的分支
git fetch origin feat/wget-1.21

# 查看变更概览
git log origin/main..origin/feat/wget-1.21 --oneline

# 查看具体文件差异
git diff origin/main...origin/feat/wget-1.21 -- archives/ knowledge/graph/draft/

# 切到分支上执行 12 项审核检查
git checkout feat/wget-1.21
python3 $SKILL_ROOT/scripts/ohc-run.py review wget-1.21-20260413
```

12 项审核检查输出示例：

```
  ✅ 1.  补丁完整性: PASS
  ✅ 2.  E编号冲突: PASS — 新增 1 个编号, 无冲突
  ⚠️ 3.  知识去重: WARN — 关键词 'openssl' 在 E015.kv 中已有匹配
  ✅ 4.  Manifest完整性: PASS
  ✅ 5.  禁止文件检查: PASS
  ✅ 6.  PROGRESS关闭: PASS
  ✅ 7.  临时文件: PASS
  ✅ 8.  knowledge_ref引用: PASS
  ✅ 9.  打包产物: PASS
  ✅ 10. 测试报告: PASS
  ✅ 11. 提交自检: PASS
  ✅ 12. 总体评估: PASS — 11 PASS, 1 WARN

  结果: 10 PASS / 2 WARN / 0 FAIL (共 12 项)
```

**主编额外关注**：

| 场景 | 怎么判断 |
|------|---------|
| 知识去重 WARN | 读草稿 `.kv`，决定：合并到已有条目？还是独立条目？ |
| test_results 全零 | 是没填还是真没测？ |
| PROGRESS 未关闭 | 协作者忘了收尾还是编译中断？ |

```bash
# 读取草稿辅助判断
cat knowledge/graph/draft/E082-draft-A7F3.kv

# 审核完毕切回 main
git checkout main
```

### 步骤 3：GitCode 平台操作

**批准合并**：

在 GitCode 平台上对 PR 执行 **Merge** 操作：
- 默认使用 **Squash 合并**，将分支上的所有 commit 压缩为一个
- 合并后 PR 自动关闭，分支可删除
- 如果 PR 标题含 `[NOSQUASH]`，使用普通 merge 保留提交历史

**拒绝 PR**：

在 GitCode 平台上 **Close PR**，并在评论中附上拒绝原因：

```
拒绝原因：
1. notes.md 未包含结束标记
2. E083 与 E020 语义重复，请合并到 E020 后重新提交
3. 补丁 0002-fix-musl-compat.patch 的 diff 格式不合法

请修复后重新发起 PR。
```

### 步骤 4：本地合并与索引重建

PR 在 GitCode 平台合并后，主编在本地同步并执行索引重建：

```bash
# 同步远程合并结果
git pull origin main

# 执行索引重建（approve 的 7 步操作）
# ① draft/ 草稿 → knowledge/graph/ 正式目录
# ② 重建 knowledge/graph/index.tsv
# ③ 重建 archives/_index.yaml
# ④ 重建 SUMMARY.md
# ⑤ 收割版本级 skill-feedback → 根级
# ⑥ 输出操作摘要
# ⑦ 提交索引更新
python3 $SKILL_ROOT/scripts/ohc-run.py approve <submission-id>

# 验证知识图谱完整性
python3 $SKILL_ROOT/scripts/ohc-run.py graph validate --verbose --coverage

# 将索引更新提交到 main
git add knowledge/graph/index.tsv archives/_index.yaml SUMMARY.md reports/
git commit -m "chore: 重建索引 — 合并 wget 1.21 编译成果"
git push origin main
```

> **为什么主编要手动重建索引**：协作者只能写 `draft/`，正式知识目录和索引文件只有主编能修改。PR 合并后，主编在本地执行 `approve` 完成知识整合和索引重建。

---

## 四、GitCode 分支和 PR 规范

### 分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能/新软件编译 | `feat/wget-1.21` |
| `fix/` | 修复问题 | `fix/curl-openssl-link` |
| `opt/` | 优化改进 | `opt/nginx-build-flags` |
| `refactor/` | 重构 | `refactor/patch-naming` |
| `docs/` | 文档更新 | `docs/update-faq` |
| `chore/` | 杂项维护 | `chore/cleanup-temp-files` |

### PR 标题规范

```
类型: 一句话描述（50 字以内）
```

**类型关键词**：`feat`、`fix`、`opt`、`refactor`、`docs`、`chore`

**特殊前缀**：
- `[NOSQUASH] feat: ...` — 要求保留完整提交历史，不使用 Squash 合并

**PR 标题示例**：

```
feat: 编译 wget 1.21 成功，含 3 个补丁
fix: 修复 curl 8.7.1 SSL 链接错误
opt: 优化 nginx 编译，禁用无用模块
[NOSQUASH] fix: 3 个独立修复（patch 格式、manifest 字段、临时文件清理）
```

### PR 描述模板

```markdown
## 背景
[为什么做这件事，软件的定位和依赖关系]

## 修改
- [具体的文件和改动列表]
- [补丁数量和用途]
- [知识草稿数量和主题]
- [测试结果摘要]

## 测试
- [ ] `submit --check` 12 项全部 PASS
- [ ] `verify-build` 通过
- [ ] 本地功能验证
```

### 合并策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| **Squash 合并**（默认） | 将分支所有 commit 压缩为一个，使用 PR 标题作为 commit message | 绝大多数场景 |
| **普通合并** `[NOSQUASH]` | 保留完整提交历史 | 分支上有多个有独立价值的提交 |
| **半线性合并** | 分支必须 rebase 到 main 最新（无 merge commit） | 所有场景（强制要求） |

### 协作者 vs 主编职责对比

| 规范项 | 协作者 | 主编 |
|--------|--------|------|
| 分支操作 | `git checkout -b feat/xxx` → 自由 commit → rebase → push | `git fetch` → 本地审核 → 平台合并 |
| 改动范围 | `archives/` + `knowledge/graph/draft/` | 所有区域 + 索引重建 |
| 自检 | `submit --check`（12 项） | `review`（12 项） + `git diff` 审核 |
| 知识操作 | `graph add --draft`（写草稿） | approve 时：草稿 → 正式 + 重建索引 |
| 反馈 | `reports/skill-feedback.md`（版本级） | 收割到根级 |
| PR 操作 | 创建 PR、修改 PR、关闭 PR | 审核 PR、合并 PR、关闭 PR |
| 禁止操作 | 修改 `index.tsv` / `SUMMARY.md` / `_index.yaml` / `SKILL.md` | 不直接改协作者的 archive（审核时除外） |

---

## 五、常见问题

### Q1: PR 被拒绝了怎么办？

查看 PR 评论中的拒绝原因，按原因修复后在同一分支上修改并重新推送：

```bash
# 确保还在功能分支上
git checkout feat/wget-1.21

# 修复问题（如关闭 notes.md、合并重复知识条目）
# ...

# 重新自检
python3 $SKILL_ROOT/scripts/ohc-run.py submit --check wget 1.21

# 提交修复并推送
git add -A
git commit -m "fix: 修复审核问题"
git rebase origin/main
git push origin feat/wget-1.21

# 在 GitCode 上原 PR 会自动更新（如果未关闭）
# 如果 PR 已关闭，重新创建 PR
```

### Q2: 知识草稿被标记为重复？

主编会判断是合并还是保留：
- 如果主编决定**合并**到已有条目 → 会在 PR 评论中说明，协作者修改草稿后重推
- 如果主编决定**保留** → approve 时自动移入正式目录，E 编号不变

### Q3: 多人编译同一个软件怎么办？

协作者通过**不同分支**隔离：
```
feat/wget-1.21    ← 协作者 A7F3 的分支
feat/wget-1.21-b2 ← 协作者 B2E1 的分支
```

如果两人都编译了同一个软件的同一版本：
- 两个 PR 同时存在，主编选择较优者合并
- 主编也可以沟通后将两人的成果合并到一个分支上

### Q4: 编译失败了也要提交 PR 吗？

是的。即使状态是 `partial` 或 `failed`，也建议提交 PR：
- 成果中可能有有价值的补丁和知识
- 主编可以合并部分成果（有用的补丁、知识草稿）
- 其他人可以在你的分支上继续

```bash
git commit -m "feat(wget): 编译 partial，含 2 个有效补丁和 1 条知识草稿"
git push origin feat/wget-1.21
# PR 标题: feat: 编译 wget 1.21 — partial，含部分有效成果
```

### Q5: 依赖其他软件怎么办？

优先使用预编译包：

```bash
# 方式 A：init-build 自动检查并安装（推荐）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build wget 1.21

# 方式 B：手动检查
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps wget
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --install wget

# 方式 C：手动安装特定依赖
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- openssl 1.1.1w
```

### Q6: rebase 时遇到冲突怎么办？

```bash
git fetch origin
git rebase origin/main

# 如果有冲突：
# 1. 查看冲突文件
git status

# 2. 手动解决冲突
# 编辑冲突文件，选择正确的版本

# 3. 标记已解决
git add <冲突文件>
git rebase --continue

# 4. 如果 rebase 过程中想放弃
git rebase --abort
```

### Q7: 已经推送了分支，想修改最后一次提交？

```bash
# 修改最后一次 commit（补充文件或修改信息）
git add <新文件>
git commit --amend -m "feat(wget): 更新提交信息"

# 强制推送（因为修改了已推送的 commit）
git push origin feat/wget-1.21 --force-with-lease
```

---

## 六、违规说明

| 违规行为 | 处理 |
|----------|------|
| 跳过 `submit --check` 直接创建 PR | 主编 review 可能 FAIL 多项，PR 被关闭，影响审核效率 |
| notes.md 未关闭 | PR 被拒绝，要求补填后重新提交 |
| 直接修改 `index.tsv` / `SUMMARY.md` / `_index.yaml` | 视为越权操作，PR 被拒绝，主编回退变更 |
| 知识图谱直接写正式目录（跳过 `--draft`） | 主编不认，需走 `--draft` 流程重新提交 |
| 不 rebase 直接推 PR | GitCode 半线性检查不通过，PR 无法合并 |
| 分支命名不规范（如 `my-branch`） | 主编要求重命名分支后重新发 PR |
| PR 标题超 50 字或格式错误 | 主编要求修改标题后重新审核 |
| 直接 push 到 `main` | 被视为严重违规，分支保护规则应阻止此操作 |

---

## 一句话记流程

**协作者**: 领任务 → 创建分支 → 编译迭代 → 整理归档 → 自检 → commit + rebase → push → 创建 PR

**主编**: 看 PR → fetch 本地审核 → 平台 Merge/Close → pull 合并 → 重建索引

**依赖**: 缺依赖 → 先查预编译包 → 没有 → 查编译顺序 → 先编依赖

---

*参照: GitCode 多人协作提交规范（Squash + 半线性合并配置）*
*适配: OpenHarmony Compile Agent v7.3 Git+PR 工作流*
