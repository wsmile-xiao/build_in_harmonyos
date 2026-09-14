# 路径 B 知识库扩展申请：PR diff 携带「删除根目录文件」补丁导致 CI checkout-pr 硬失败

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#7094 devmem2 0.2
- **关联 PR**：`!9172`（`feat/devmem2-0.2`，配方 PR，CI build #43399 校验通过）
- **知识草稿**：`knowledge/drafts/devmem2-0.2-prdiff-root-file-deletion-apply-fail.kv` / `.md`
- **草稿 ID**：`DRAFT-DEVMEM2-PRDIFF-ROOT-FILE-DELETION-APPLY-FAIL`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/devmem2-0.2`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

CI 的 `checkout-pr` 是**每个** PR 都会过的步骤，且它的失败**早于所有 conan 门禁**，
日志里不含任何配方信息。一旦命中"PR diff 携带删除补丁"，重试必然复现、现象又与
配方无关，排查者极易得出"CI 平台卡住 / 平台改了规则"的错误结论并开始盲改代码。
本条给出**一行判据**（`curl <PR>.diff | grep 'deleted file mode'`）与**一个确定性
处置**（把分支重建到当前 main tip，使 merge-base 前移），可直接被后续任何 PR 套用。

## 二、症状与最小复现

```
--- checkout-pr ---                  ← 注意：L0/L1/test_package 全都没执行
error: pr_body_final.md
pr_body_final.md: does not exist in index
```

构建步骤表：`git-clone ✅ → checkout-pr ❌ → conan-setup ... `

复现要素三条（缺一不可）：

1. 分支的 **fork 点（merge-base）** 上存在某个仓库**根目录**文件
   （实测：他人 PR 误合并进 main 的 `pr_body_final.md`，内容是 nanoflann 1.12.1 的 PR 正文）；
2. 该分支上此文件被删除过；
3. 当前 main tip 也没有这个文件 —— 于是 worker 的工作树里不存在待删文件。

判定（一行）：

```bash
curl -sSL https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/<PR>.diff \
  | grep -n 'deleted file mode' -B2 | head
# → diff --git a/pr_body_final.md b/pr_body_final.md
#   deleted file mode 100644
```

## 三、根因

CI 的 `checkout-pr` **不 checkout 分支**，而是
「clone 默认分支 → `git reset --hard HEAD && git clean -fdx` → curl PR diff →
`git apply` / `git apply --3way` / `patch -p1`」；
而 GitCode 计算 PR diff 的基准是 **merge-base（fork 点）**，不是 main tip。
于是当 fork 点与 main tip 对某文件存在"删除"差异时，diff 必携删除补丁，
而 worker 工作树是 main tip —— **patch 的 preimage 不在工作树里**，apply 注定失败
（`--3way` 还会因 shallow clone 缺 blob 而报 `does not exist in index`）。

## 四、处置（可复用步骤）

```bash
git fetch --depth=1 origin main
git checkout -B <branch> origin/main
git checkout <old-tip> -- archives/<letter>/<name>/     # 只取本次交付文件
git commit -m "chore: rebuild branch on current main"
git push -f origin <branch>
```

重建后 merge-base 前移、diff 只含新增文件，checkout-pr 立即通过。
**不要重复 `/rebuild`**：这是确定性冲突，重试必然复现。

## 五、验证证据

| 项 | 证据 |
|---|---|
| 阻塞期 | build **#43367 / #43373 / #43388**：`checkout-pr ❌`，日志含 `pr_body_final.md: does not exist in index` |
| 判据 | `curl .../pull/9172.diff \| grep 'deleted file mode'` → 命中 `pr_body_final.md` |
| 处置后 | build **#43394** 起进入 conan 阶段；**#43399 `CI 校验通过`** |
| 反证"平台改了规则" | `git diff <旧 main> origin/main -- ci/` 仅 `ci/config/build_timeouts.txt` +6 行，`build_and_test.sh` 零改动；同窗内他人 PR 仍有 pass |

## 六、查重声明

- **E510**（toybox patch 无法处理带路径层级/fuzz 的上游补丁）：同属"补丁 applier 失败"，
  但 E510 发生在**配方内 `patches/` 对上游源码**的应用，本条发生在 **CI 的 PR diff 应用**；
  阶段、对象、判据、处置全不同（E510 换 GNU patch，本条重建分支），**不合并**。
- 正式库以 `does not exist in index` 检索仅命中 E510 一条，语境无关。
- 本条为 CI 基础设施层的**新增失败模式**（前置步骤失败掩盖全部门禁）。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否需要把该判据补进 `docs/ADAPTATION_GUIDE.md` 或 CI 失败诊断表
   （建议：`checkout-pr` 失败时自动附一行 `grep 'deleted file mode'` 提示）？
3. 分支重建（force-push 自己分支）作为标准处置是否被认可？
