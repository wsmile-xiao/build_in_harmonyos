# 路径 B 知识库扩展申请：任务版本号含连续两点时 R40/L0n 分支名门禁物理不可满足

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6607 mlddc 1.0..1（平台给定 taskBranch `feat/mlddc-1.0..1`）
- **关联 PR**：`!9124`（`feat/mlddc-1.0-1`，配方 PR，CI build #42994 校验通过）
- **知识草稿**：`knowledge/drafts/mlddc-1.0-1-dotdot-version-branch-gate-r40.kv` / `.md`
- **草稿 ID**：`DRAFT-MLDDC-DOTDOT-VERSION-R40-BRANCH-GATE`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/mlddc-1.0-1`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"而不是"个案记录"

R40/L0n 是**每个** conan 配方 PR 都会过的门禁项；而"版本号含 git 非法字符"这一
情形一旦出现，**任何**贡献者按平台给定 taskBranch 操作都会 100% 撞上，且现象是
"配方其余门禁全绿、只有 L0n 红"，极易被误判为配方问题而陷入盲改循环。本条把
判据（`git check-ref-format`）、成因（数据集版本号拼接缺陷）、处置（按 CI 自身
`+`→`-` 归一化语义收敛）三者一次讲清，可被后续任何同类任务直接套用。

## 二、症状与最小复现

```
o[step] L0j: [ok] version not in registry yet (first publish)
o[step] L0k: [ok] commands.json valid (type=tool)
o[step] L0m: [ok] directory structure valid
o[step] L0n: [error] branch name mismatch (R40) — 分支完全不包含 包名-版本号
o       分支 'feat/mlddc-1.0-1'（去前缀后 'mlddc-1.0-1'）不包含 'mlddc-1.0..1'
o[fail] mlddc/1.0..1 — L0 quality gate failed: branch_name_r40
```

判据（一行即可证伪，不必消耗 CI 轮次）：

```bash
git check-ref-format "refs/heads/feat/mlddc-1.0..1"; echo rc=$?   # rc=1
```

服务端同样拒绝建分支：

```
POST /repos/OpenHarmonyPCDeveloper/build_in_harmonyos/branches
     ?branch_name=feat/mlddc-1.0..1 → HTTP 400
```

CI 提示里给出的"正确示例" `feat/mlddc-1.0..1` 本身就是**不可 push 的分支名**，
说明该缺陷来自任务元数据而非配方。

## 三、根因

`ci/conan/build_and_test.sh` 的 L0n 是逐字比较，且只做 `+ → -` 归一化：

```bash
EXPECTED_TAG="${pkg_name}-${pkg_ver}"
EXPECTED_TAG_NORM=$(echo "${EXPECTED_TAG}" | tr '+' '-')
BRANCH_BASE="${CI_BRANCH##*/}"; BRANCH_BASE=$(echo "$BRANCH_BASE" | tr '+' '-')
[ "${BRANCH_BASE}" = "${EXPECTED_TAG_NORM}" ]     # 必须精确相等
```

当 `${pkg_ver}` 含连续两点时，期望值 `mlddc-1.0..1` 在 git ref 规范下**不存在**，
于是门禁的取值域为空集 —— 无论取什么合法分支名都不可能通过。属**任务元数据与
门禁规则取值域不交集**，非配方缺陷。数据集层面可见同一批次同时存在
mlddc `1.0.1`（任务 #6651）与 `1.0..1`（任务 #6607）两条记录。

## 四、处置（可复用步骤）

1. `git check-ref-format "refs/heads/<taskBranch>"` 证伪，停止盲试分支名；
2. 按 CI 自身归一化语义（R40 注释原文：`+ → -`，Debian 风格版本后缀）把版本
   收敛为 git 合法等价形式：`1.0..1` → **`1.0-1`**；
   - 版本目录改名、`conanfile.version`、`conandata.yml`、版本级 `manifest.yaml`、
     `test_package/MANIFEST.yml`、软件级 `commands.json` 的 `versions` 键全部同步；
   - 分支 `feat/mlddc-1.0-1` 去前缀后精确等于期望值，L0n 通过；
3. 在 PR 正文首段写明归一化依据（含 git 与服务端原始报错），避免评审误判；

**反例**：不要直接把版本目录改成同批次另一任务的版本号（撞 R37/L0j，且抢占他人
任务版本、与他人的既有 PR 冲突）。也不存在"多试几个分支名"的解——取值域是空集。

## 五、验证证据

| 项 | 证据 |
|---|---|
| 未归一化 | PR !9124 build **#42876**：L0j/L0k/L0m 全 `[ok]`，仅 L0n `[fail] branch_name_r40` |
| 归一化后 | PR !9124 build **#42879 / #42994**：`CI 校验通过`，`[ok] L0: All quality gate checks passed` |
| 本地构建 | `conan create archives/m/mlddc/1.0-1 --profile:host=ohos-aarch64` 退出码 0 |
| 产物 | `ELF64 / AArch64 / ET_DYN(PIE)`，`DT_NEEDED = libc.so` |

## 六、查重声明

- **E416**（L0m-5 slug / 双 case 目录）与本条同属 L0 系列门禁，但门禁项不同
  （L0m-5 vs L0n/R40）、失败信息不同、处置动作不同（改目录名 vs 归一化版本号），
  **不合并**。
- **E510**（toybox patch 与 `does not exist in index`）属补丁应用层，与本条无关。
- 正式库内以门禁项字面（`branch_name_r40`）检索为 **0 命中**，本条为新增门禁
  误报模式。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 版本号归一化 `1.0..1 → 1.0-1` 的处置是否被认可为对**数据集缺陷**的合规应对
   （而非"改版本号规避门禁"）？若平台侧后续修正任务元数据，本条处置是否需
   与之对齐？
3. 是否需要把该归一化规则补进 `docs/ADAPTATION_GUIDE.md` 的 R40 说明，避免后续
   贡献者重复踩坑？
