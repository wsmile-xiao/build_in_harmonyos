# DRAFT-10000 — build_and_test.sh G0a zsh 空目录 null-glob 误报（框架层）

## 错误特征

`ohc-run.py finish <软件> <版本>` 的 W3 本地 CI 模拟失败，输出：

```
[step] G0: Knowledge graph integrity check...
[fail] G0a: knowledge/graph/draft/ 目录存在 31 个草稿 — 草稿只能放在 knowledge/drafts/
G0_RESULT=fail: 1 errors
```

注意：`31` 恰好是仓库根目录的顶层条目数（CONTRIBUTING.md / README.md / SKILL.md /
archives / ci / knowledge / ...），与包本身无关。

## 触发条件

- 阶段: finish Step 3.5 (W3 本地 CI 模拟)
- 前置: 仓库存在 `knowledge/graph/draft/` 目录且**为空**（未跟踪的空目录）
- 任何软件包（无论编译是否成功）都会被阻塞

## 根因分析

`ci/conan/build_and_test.sh` 的 G0a 检查：

```zsh
if [ -d "${GRAPH_DIR_G0}/draft" ]; then
    G0_DRAFT_COUNT=$(ls -1 "${GRAPH_DIR_G0}/draft"/*.kv(N) 2>/dev/null | wc -l)
    if [ "${G0_DRAFT_COUNT}" -gt 0 ]; then ... fail ...; fi
fi
```

zsh 的 `(N)` null-glob 限定符在**无匹配**时会把**整个 glob 单词**（含目录路径）
移除，命令退化为 `ls -1`（无参数）→ 列出当前工作目录。W3 的 cwd 是仓库根
（31 个顶层条目）→ `wc -l` = 31 → 误报。bash 行为不同：未匹配 glob 保持字面量，
`ls` 报 "No such file" → 计数 0，不会误报。

另发现框架不一致：skill 版 `scripts/ohc/graph.py` 的 `graph add --draft` 把草稿写到
`knowledge/graph/draft/`（已废弃位置），而仓库版 graph.py 写到 `knowledge/drafts/`
（CI G0a / graph.py C12 / `graph promote` 均以 `knowledge/drafts/` 为准）。

## 解决方案

### 推荐方案（框架层，需单独 PR）
`build_and_test.sh` G0a 计数改为不会退化为裸 ls 的写法：

```zsh
G0_DRAFT_COUNT=$(ls -1d "${GRAPH_DIR_G0}/draft"/*.kv(N) 2>/dev/null | wc -l)
# 或
G0_DRAFT_COUNT=$(find "${GRAPH_DIR_G0}/draft" -maxdepth 1 -name '*.kv' 2>/dev/null | wc -l)
```

### 协作子任务解除阻塞（不改 ci/）
`knowledge/graph/draft/` 是未跟踪的空目录（git 不跟踪空目录），框架自身也要求它
不存在，删除后重跑 finish 即可：

```bash
rmdir /storage/Users/currentUser/runner/build_in_harmonyos/knowledge/graph/draft
python3 <skill>/scripts/ohc-run.py finish <软件> <版本> built --project-dir <repo>
```

若目录非空（含旧草稿），先把草稿移入 `knowledge/drafts/` 再删除目录。

### 禁止做法
- ❌ 往 `knowledge/graph/draft/` 写任何 `.kv` 草稿（触发 G0a/C12，且 promote 不读）
- ❌ 修改 `ci/` 脚本（框架 PR 由主编单独提交）

## 验证

```bash
# 修复前（目录存在且为空时误报）：
zsh -c 'ls -1 "$(pwd)/knowledge/graph/draft"/*.kv(N) 2>/dev/null | wc -l'   # → 31
# 删除空目录后 G0a 守卫为假，检查被跳过：
[ -d knowledge/graph/draft ] && echo "exists" || echo "absent"             # → absent
```
