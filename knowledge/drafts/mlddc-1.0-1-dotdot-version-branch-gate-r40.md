# 任务版本号含连续两点时 R40/L0n 分支名门禁物理不可满足（1.0..1 → 1.0-1）

> Draft: `DRAFT-MLDDC-DOTDOT-VERSION-R40-BRANCH-GATE`
> Stem: `mlddc-1.0-1-dotdot-version-branch-gate-r40` — 与同 stem 的 `.kv` 成对
> 实例：mlddc 1.0..1（平台任务 #6607，配方 PR !9124）

## 基本信息

- **ID**: DRAFT-MLDDC-DOTDOT-VERSION-R40-BRANCH-GATE
- **严重度**: 2
- **类别**: ci-gate, platform-metadata, branch-naming
- **触发工具**: ci（conan build_and_test.sh 的 L0 质量门禁）
- **阶段**: verification（L0n / R40 分支名匹配检查）

## 错误特征

```
o[step] L0n: Checking branch name matches package (R40)...
o[error] L0n: branch name mismatch (R40) — 分支完全不包含 包名-版本号
o       分支 'feat/mlddc-1.0-1'（去前缀后 'mlddc-1.0-1'）不包含 'mlddc-1.0..1'
o[hint] 分支名必须以 包名-版本号 结尾，例如：
o         mlddc-1.0..1 / feat/mlddc-1.0..1 / fix/mlddc-1.0..1
o[fail] mlddc/1.0..1 — L0 quality gate failed: branch_name_r40
oL0_RESULT=fail: gate failed: branch_name_r40
```

注意 hint 里给出的"正确示例"本身就是**不可 push 的分支名** —— 这是数据集缺陷直接
泄漏到了 CI 提示里。

## 可复现问题

平台任务 `#6607` 的版本号字面为 `1.0..1`（连续两点），`taskBranch` 为
`feat/mlddc-1.0..1`。三步验证该分支名物理不存在：

```bash
$ git check-ref-format "refs/heads/feat/mlddc-1.0..1"; echo rc=$?
rc=1
$ git check-ref-format --branch "feat/mlddc-1.0..1"
fatal: 'feat/mlddc-1.0..1' is not a valid branch name
```

GitCode 建分支 API 同样拒绝：

```
POST /repos/OpenHarmonyPCDeveloper/build_in_harmonyos/branches
     ?branch_name=feat/mlddc-1.0..1&refs=<sha>
-> HTTP 400: Cannot start with - . refs/heads/ refs/remotes/, special characters
   such as spaces and single quotes and double quotes and [ \\ < ~ ^ : ? * ! ( ) |
   are not supported, the end with . / .lock is not supported
```

于是把版本目录照抄成 `archives/m/mlddc/1.0..1/`、分支取任何合法名字（例如
`feat/mlddc-1.0-1`）后，L0 其余门禁全绿、只有 L0n 必然红：

```
o[step] L0j: ... [ok] version not in registry yet (first publish)
o[step] L0k: ... [ok] commands.json valid (type=tool)
o[step] L0m: ... [ok] directory structure valid
o[step] L0n: ... [fail] branch_name_r40       ← 只有这一项红
```

## 根因分析

CI 的门禁实现（`ci/conan/build_and_test.sh` L0n）是**逐字字符串比较**：

```bash
EXPECTED_TAG="${pkg_name}-${pkg_ver}"
EXPECTED_TAG_NORM=$(echo "${EXPECTED_TAG}" | tr '+' '-')
BRANCH_NORM=$(echo "${CI_BRANCH}" | tr '+' '-')
BRANCH_BASE="${BRANCH_NORM##*/}"
[ "${BRANCH_BASE}" = "${EXPECTED_TAG_NORM}" ]   # 必须精确相等
```

门的语义没错，但**当版本号本身含 git 非法字符时，期望值在 git 世界里不存在**：
ref 名的连续两点是 `git check-ref-format` 的硬性禁止项，服务端亦同步拒绝，
因此不存在任何能既有对应 git 分支、又与期望值相等的分支名。这不是配方问题，
而是**任务元数据（版本号）与 CI 门禁规则取值域不交集**。

数据集层面的成因也可推断：同一批任务里 mlddc 同时存在 `1.0.1`（任务 #6651，
分支 `feat/mlddc-1.0.1`）与 `1.0..1`（任务 #6607）两条记录，后者是把
`<版本> + "." + <修订>` 拼接时多写了一个点的产物。

## 已试失败方向

- **直接把版本目录写成 `1.0..1`、分支随便取合法名** → L0n 必红（本文实测）。
- **试图用 API 强行创建 `feat/mlddc-1.0..1`** → 服务端 400，不成立。
- **改投同批次另一个任务的版本号（1.0.1）** → 撞 R37/L0j 版本占用，且与他人的
  既有 PR（!8726）冲突；即便在对方合并前抢跑，也属抢占他人任务版本，不可取。
- **只改分支名不改版本目录** → 期望值仍由目录名推出，L0n 依旧红。

## 最终方案（step-by-step）

1. **先证伪，别猜**：`git check-ref-format "refs/heads/<taskBranch>"` 返回非 0，
   即说明该任务分支不可 push，立刻停止"试一个分支名跑一轮 CI"的循环。
2. **取 CI 自己的归一化语义**：`build_and_test.sh` 的 R40 注释原文写着
   「归一化：+ → -（Debian 风格版本后缀如 1.4+dfsg.1 → 1.4-dfsg.1）」。
   据此把 `1.0..1` 收敛为 **`1.0-1`**：
   - 版本目录 `archives/m/mlddc/1.0-1/`
   - `conanfile.version = "1.0-1"`、`conandata.yml` 注释、`notes.md`、版本级
     `manifest.yaml`、`test_package/MANIFEST.yml` 的 `package:` 一并同步
   - 软件级 `commands.json` 的 `versions` 键加 `"1.0-1"`
   - 分支名 `feat/mlddc-1.0-1` → 去前缀后 `mlddc-1.0-1` **精确等于**期望值
3. **在 PR 正文首段写清归一化依据**（任务版本、taskBranch、git 与服务端双重
   拒绝的原始报错、所引用的 CI 归一化注释），避免评审误判成"版本号写错"，
   也留下可审计的换算链条。
4. 归一化后 L0j/L0k/L0m/L0n 全绿，CI 校验通过（实测 build #42879、#42994）。

```
# 归一化后 L0 全绿
o[step] L0j: Checking version collision with registry (R37)... [ok] first publish
o[step] L0k: Checking commands.json for CLI tools (R38)...    [ok] commands.json valid
o[step] L0m: Checking directory structure (R39)...            [ok] directory structure valid
o[step] L0n: Checking branch name matches package (R40)...    [ok] branch 'feat/mlddc-1.0-1'
o[ok] L0: All quality gate checks passed
```

## 边界与查重

- 与 **E416**（官方大写元数据目录与新增小写 recipe 目录双 case 并存，L0m-5 slug 门禁）
  的区别：E416 处理的是**目录名大小写/ slug 形态**，本条处理的是**版本号含 git 非法
  字符导致分支名不可构造**，两者都命中 L0 系列门禁但门禁项不同（L0m-5 vs L0n/R40）、
  失败信息不同、处置动作不同（改名 vs 归一化版本）。
- 与 **E510**（toybox patch 无法处理带路径层级/fuzz 的补丁）无重叠：E510 的
  `does not exist in index` 是 patch 应用层，本条与补丁无关。
- 正式知识库中 `branch_name_r40` / `L0h` 一类**门禁项字面**检索为 0 命中，
  本条为新增门禁误报模式，非既有条目复用。

## 关联

- 配方 PR：**!9124**（mlddc 1.0-1 适配 HarmonyOS PC，分支 `feat/mlddc-1.0-1`）
- 平台任务：#6607（mlddc 1.0..1）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
