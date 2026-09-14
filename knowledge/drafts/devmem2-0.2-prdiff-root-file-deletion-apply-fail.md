# PR diff 携带「删除根目录文件」补丁导致 CI checkout-pr 硬失败

> Draft: `DRAFT-DEVMEM2-PRDIFF-ROOT-FILE-DELETION-APPLY-FAIL`
> Stem: `devmem2-0.2-prdiff-root-file-deletion-apply-fail` — 与同 stem 的 `.kv` 成对
> 实例：devmem2 0.2（任务 #7094，配方 PR !9172）

## 基本信息

- **ID**: DRAFT-DEVMEM2-PRDIFF-ROOT-FILE-DELETION-APPLY-FAIL
- **严重度**: 2
- **类别**: ci-mechanism, git-diff, shallow-clone
- **触发工具**: ci（buildbot 的 checkout-pr 步骤）
- **阶段**: checkout（早于 L0/L1 等所有 conan 门禁）

## 错误特征

```
--- checkout-pr ---
hif [ -n "<sha>" ]; then   git config --global --add safe.directory "*"   && echo "PR 构建: 清理工作区并应用 PR 9172 diff patch"   && git reset --hard HEAD   && git clean -fdx   && ( curl -sSfk ... "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9172.diff" -o pr.diff || ... ) && ( git apply --whitespace=nowarn pr.diff || git apply --3way --whitespace=nowarn pr.diff || patch -p1 --fuzz=3 < pr.diff ...

error: pr_body_final.md
pr_body_final.md: does not exist in index
```

构建步骤表里 `checkout-pr` ❌，而 `conan-setup` 之后的一切（L0/L1/test_package）**根本没执行**。

## 可复现问题

1. 分支 fork 点（merge-base）上存在某个**仓库根目录**文件——实测是他人 PR 误合并进
   main 的 `pr_body_final.md`（内容是 nanoflann 1.12.1 的 PR 正文）。
2. 该分支上此文件被删过（`git rm`），且删除后 main 也把它移除，于是

   ```
   $ git ls-tree --name-only origin/main | grep pr_body     # 空：main tip 已无此文件
   $ git ls-tree --name-only origin/<branch> | grep pr_body # 空：分支 tip 也无
   ```

3. 但 PR diff 里**仍然带着这条删除补丁**（因为 diff 的基准是 fork 点，不是当前 main）：

   ```
   diff --git a/pr_body_final.md b/pr_body_final.md
   deleted file mode 100644
   index 830d9d94..0000000000
   --- a/pr_body_final.md
   +++ /dev/null
   @@ -1,72 +0,0 @@
   ```

4. CI 的 worker 工作树是**当前 main tip**（没有该文件）→ `git apply` 找不到待删文件 →
   `--3way` 因 shallow clone 缺该 blob 报 `does not exist in index` → `patch` 失败 →
   checkout-pr exit 1。

判定一行：

```bash
curl -sSL https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/<PR>.diff \
  | grep -n 'deleted file mode' -B2 | head
```

## 根因分析

CI 的 checkout-pr **不 checkout 分支**，而是「clone 默认分支 → `git reset --hard HEAD &&
git clean -fdx` → curl PR diff → `git apply`」。而 GitCode 计算 PR diff 的基准是
**merge-base（fork 点）**。当 fork 点与当前 main tip 之间存在「该文件被删除」的差异时，
diff 必然携带删除补丁，而 worker 的工作树却是 main tip —— **patch 的 preimage 不在
工作树里**，apply 注定失败。

这类失败的迷惑性极强：
- 失败步骤是 `checkout-pr`，**早于** 全部 conan 门禁，日志里看不到任何配方信息；
- 该步骤脚本里同时含 `curl`（有超时/重试逻辑），极易被误判为网络问题；
- 重试无效（确定性冲突），于是排查者常得出"CI 平台卡住/平台改了规则"的错误结论。

实测同一 PR 的对照：build **#43373 / #43388** 均 checkout-pr ❌；重建分支后
**#43394** 起进入 conan 阶段并通过。

## 已试失败方向

- **重复 `/rebuild`** → 确定性冲突，必然复现（`#43367 → #43373` 两次同因）。
- **怀疑平台改了 CI 脚本** → 证伪：`git diff <旧 main> origin/main -- ci/` 显示
  `build_and_test.sh` 零改动（只多了 `ci/config/build_timeouts.txt` 6 行），
  且同一时间窗内他人 PR 仍有 pass。
- **怀疑网络** → 部分成立（早期确有 curl 超时），但重试后 curl 成功、apply 仍失败，
  说明真正的阻塞点是 apply 冲突而非网络。

## 最终方案（step-by-step）

1. **判据**：`curl <PR>.diff | grep 'deleted file mode'`；若携带根目录文件的删除补丁，
   且该文件在当前 main tip 不存在 → 命中本条。
2. **重建分支到当前 main tip**（让 merge-base 前移，diff 只含本次新增文件）：

   ```bash
   git fetch --depth=1 origin main
   git checkout -B <branch> origin/main
   git checkout <old-tip> -- archives/<letter>/<name>/      # 只取本次交付的文件
   git commit -m "chore: rebuild branch on current main"
   git push -f origin <branch>
   ```

3. 重建后 checkout-pr 立即通过（实测 #43394 起 L0 全绿并进入 conan create）。
4. **防复发**：仓库根目录不放任何临时文件（CI G0e 根目录白名单只允许
   `.gitignore/.gitattributes/BUILD.gn/CONTRIBUTING.md/KNOW_YOUR_WHY.md/LICENSE/
   README.md/SKILL.md/SUMMARY.md/oh-package.json`）；PR 草稿写进 PR 描述或
   `archives/<l>/<名>/` 下（`reports/` 被 .gitignore 全局忽略，需用版本目录根）。

## 边界与查重

- 与 **E510**（toybox patch 无法处理带路径层级/fuzz 的上游补丁）的区别：E510 发生在
  **配方内 patch 应用**（`patches/` 目录、`patch -p1` 对上游源码），本条发生在
  **CI 的 PR diff 应用**（checkout-pr 步骤、diff 含删除补丁），两者工具同为 git/patch
  但阶段、对象、判据、处置均不同，**不合并**。
- 正式库内以 `does not exist in index` 检索仅命中 E510 一条，且其语境为 toybox
  `patch` 对上游补丁的路径层级处理，与本条无关。
- 与 **E416 / R40 分支名类** 无交集（本条与门禁规则无关，是 CI 基础设施行为）。

## 关联

- 配方 PR：**!9172**（devmem2 0.2 适配 HarmonyOS PC，分支 `feat/devmem2-0.2`）
- 平台任务：#7094（devmem2 0.2）
- 对照 build：#43373 / #43388（checkout-pr ❌）→ #43394 / #43399（CI 校验通过）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
