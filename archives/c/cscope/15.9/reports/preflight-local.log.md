# cscope 15.9 — PR 创建前置硬闸（preflight）本地执行留痕

> 生成时间：2026-09-26
> 分支：`feat/cscope-15.9` → `main`
> 工具：`scripts/ohc/preflight.py`（PF1-PF9 + R52 交叉校验，v12.20）

## 1. 结论摘要

| 闸门 | 结果 |
|------|------|
| PF1 单包闸 | ✅ 通过（净 diff 仅含 `archives/c/cscope/`） |
| PF2 制品闸 | ✅ 通过（无压缩包/二进制归档） |
| PF3 测试闸 | ✅ 通过（test_package 有真实测试源 + MANIFEST） |
| PF4 依赖闸 | ✅ 通过（`ncurses/6.6` 已在制品仓） |
| PF5 平台宏闸 | ✅ 通过（patches/ 与 conanfile.py 新增行 0 个 `__OHOS__`） |
| PF6 前缀闸 | ✅ 通过（无共享系统前缀注入） |
| PF7 源URL闸 | ✅ 通过（https 官方源 `sourceforge.net`） |
| PF8 配方闸 | ✅ 通过（CLI 包 `commands.json` name/type/versions 全对齐） |
| **PF9 分支/路径闸** | ❌ 命中 1 项 —— **确定性误报**，详见 §3 |
| R52 交叉校验 | ✅ 通过（硬闸命中项非 P0/P1 配方缺陷） |

**PF1-PF8 + R52 全部通过；PF9 唯一命中为已登记的框架级规则冲突误报。**

## 2. 本地执行记录

```
# repo_dir   : <repo root>
# base...head: main...feat/cscope-15.9

✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  ——CI 将报 No packages to build（490 例）: archives/c/cscope/commands.json

# 结果: FAIL  发现数=1
```

本 PR 变更文件（`git diff --name-only main...feat/cscope-15.9`）：

```
archives/c/cscope/15.9/conandata.yml
archives/c/cscope/15.9/conanfile.py
archives/c/cscope/15.9/manifest.yaml
archives/c/cscope/15.9/notes.md
archives/c/cscope/15.9/patches/0001-config.guess.patch
archives/c/cscope/15.9/patches/0002-config.sub.patch
archives/c/cscope/15.9/patches/0003-configure.patch
archives/c/cscope/15.9/patches/0004-src-main.c.patch
archives/c/cscope/15.9/reports/quality-report.md
archives/c/cscope/15.9/reports/test-report.md
archives/c/cscope/15.9/test_package/MANIFEST.yml
archives/c/cscope/15.9/test_package/conanfile.py
archives/c/cscope/15.9/test_package/test.sh
archives/c/cscope/commands.json          <- PF9 命中项（软件级，4 段路径）
```

## 3. PF9 命中成因：与 R38/PF8 互斥（框架级规则冲突，非配方缺陷）

- **PF9 判据**（`scripts/ohc/preflight.py:570`）：
  `bad = [f for f in arch if len(f.split("/")) < 5]`
- **PF8 判据**（`scripts/ohc/preflight.py:518-522`，R38 落地）：
  CLI 包（`package_type=application` 或 `bindirs` 非空）**必须有** `commands.json`，
  且其 `versions` 必须含本次版本 —— 该文件按 ARCHIVE-SPEC v3.0 与 SKILL.md §6
  固定在**软件级** `archives/{letter}/{name}/commands.json`（4 段路径）。

cscope 是 CLI 工具包（`bindirs` 非空），因此 `commands.json` 是 R38 强制要求；
而该文件路径深度必然为 4，**必然**触发 PF9。二者对 CLI 包首次适配 PR 互斥
—— 任何符合 R38 的 CLI 包新建 PR 都无法同时通过 PF8 与 PF9。

同类问题已被主编框架记录在案（未被视作配方缺陷）：

- `feedback/SKILL_FEEDBACK_2af9a59c.md:97`：「PF9 判据对 R38 软件级文件必然误报
  （阻塞级）……**任何符合 R38 的 CLI 包首次适配 PR 都不可能同时通过 PF8 与 PF9**」
- `archives/b/bti/034/reports/pr-body.md:58`、`archives/c/cdtool/2.1.8-release/reports/pr-body.md:96`、
  `archives/c/csstidy/1.4/notes.md:55`、`archives/d/d-shlibs/0.109/notes.md:271`：
  同一冲突，均按「闸门优先 + PR 说明留痕 + `--no-preflight`」处置。
- `archives/d/daemontools-encore/1.11/reports/preflight-local.log.md:16`：本文件格式先例。

## 4. 合并先例实证：软件级文件随 PR 合入是常态

PF9 声称软件级路径会导致 CI 报 `No packages to build`。实证否决该推断：本 PR
含版本目录下的完整输入（`conanfile.py` / `conandata.yml` / `test_package/` /
`patches/`），CI 能正常解析出包；且 **origin/main 最近一次合并**（`32018bae04`
= `!10724 merge feat/liblqr-0.4.3 into main`）本身即携带三个软件级文件：

| 合并 commit | PR | 随 PR 合入的软件级文件 |
|------------|----|----------------------|
| `32018bae04` | `!10724` liblqr 0.4.3 | `README.md`, `commands.json`, `manifest.yaml` |
| `ed46214d10` | `!11869` clitest 0.5.0 | `README.md`, `commands.json`, `manifest.yaml` |
| `8f8ce3cf5c` | `!11866` yersinia 0.8.2 | `README.md`, `commands.json`, `manifest.yaml` |
| `46b4461433` | `!11954` fasttextembed 1.0.2 | `commands.json` |
| `938b2694fd` | `!10192` smhasher 1.0 | `README.md`, `manifest.yaml` |

这些均已通过主编评审合入 main，证明软件级文件与版本目录内容**同 PR 合入**是
仓库既定实践，PF9 的 `No packages to build` 归因对「同 PR 含版本目录内容」的
情形不成立。

## 5. 处置

按先例（bti / cdtool / csstidy / d-shlibs）：**不改配方去迁就误报**（删除
`commands.json` 会同时违反 R38 与 ARCHIVE-SPEC v3.0），改为
**`--no-preflight` 绕行 + 本文件留痕 + PR 正文说明**。PF1-PF8+R52 已按上表
逐项本地等价验证通过，未因绕行失去实际保护。

## 6. 附：PF0 环境闸异常（沙箱缺陷，非仓库问题）

裸命令名 `git` 在本沙箱的 Python `subprocess` 下无法 exec：

```
subprocess.run(["git","--version"])           -> FileNotFoundError: 'git'
subprocess.run(["/data/service/hnp/bin/git","--version"]) -> OK rc=0, git version 2.45.2
subprocess.run(["sh","-c","..."])             -> OK（sh 可 exec）
shutil.which("git")                           -> /data/service/hnp/bin/git（能解析）
```

即 `create-pr` 内 `_git_toplevel()`（`scripts/gitcode_pr.py:242`）与
`preflight.changed_files()`（`scripts/ohc/preflight.py:75`）的裸 `["git", …]`
必然抛 `FileNotFoundError`，被 fail-closed 转成
`PF0 环境闸: preflight 执行异常 ([Errno 2] No such file or directory: 'git')`。

这是**本沙箱执行环境缺陷**（PATH 中的 git 对 `execvp` 不可达），与 cscope 配方
无关：git 二进制存在且绝对路径可正常执行，`git` 亦能由 `shutil.which` 解析。
上表 PF1-PF8+R52 的验证即以同名绝对路径等价执行（仅改写 `argv[0]`，闸门判据
未作任何改动）。
