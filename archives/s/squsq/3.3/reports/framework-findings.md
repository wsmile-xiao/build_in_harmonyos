# squsq 3.3 适配过程中发现的框架/平台问题（提交 PR 前需知）

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。

本文件记录**本包之外**的两处问题，供 `submit` / `feedback` 阶段使用；均已给出可复现证据，
未修改任何框架文件（W2 原子性：框架文件必须单独提 PR）。

## 1. PF9 路径闸误拦软件级元数据（框架缺陷，会导致 `submit` 建不出 PR）

**现象**：官方 `scripts/ohc/preflight.py` 对 squsq 的 PR 变更集报告 1 项拦截：

```
FAIL: PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
      ——CI 将报 No packages to build（490 例）:
      archives/s/squsq/README.md, archives/s/squsq/commands.json, archives/s/squsq/manifest.yaml
```

**判据**：`preflight.check_branch_and_paths()` 把 `len(f.split("/")) < 5` 的 archives 路径一律判为
"缺版本目录层"。

**为什么是误拦**：

* `commands.json` 由 **R38 强制要求放在软件级目录**（`archives/<字母>/<包>/commands.json`），
  同时 **PF8 又要求 CLI 包必须有 commands.json** —— PF8 与 PF9 对新 CLI 包互相矛盾；
* `README.md` / `manifest.yaml` 同样是 ARCHIVE-SPEC §6 规定的软件级文件；
* main 分支里大量先例就是 depth-4：

  ```
  $ git ls-tree -r --name-only origin/main -- archives/j/jellyfish archives/c/cronutils
  archives/c/cronutils/commands.json
  archives/j/jellyfish/README.md
  archives/j/jellyfish/commands.json
  archives/j/jellyfish/manifest.yaml
  ```

* PF9 的单元测试 `tests/test_v1220.py::test_pf9` 只覆盖 depth-5 路径与 depth-4 的
  `archives/d/demo/readme.txt`，从未考虑 R38 规定的软件级元数据。

**影响**：任何一个首次新增的 CLI 包，提交 PR 时都会被 PF9 拦下。

**建议修复**：PF9 对 `archives/<字母>/<包>/{commands.json,README.md,manifest.yaml}` 白名单放行。

**本次采取的处置**：不动框架代码；如实报告，并保留 `--no-preflight` 作为建 PR 时的逃生口
（由用户决定）。

## 2. OHOS/musl 平台：Python `subprocess` 用裸命令名必然失败（平台缺陷）

**现象**：技能脚本里所有 `subprocess.run(["git", ...])` 在本机抛 `FileNotFoundError`：

```
$ python3 scripts/ohc/preflight.py . origin/main <commit>
✗ PF0 环境闸: 无法计算变更文件（[Errno 2] No such file or directory: 'git'）——fail-closed 拦截
```

**根因取证**：

```
$ python3 -c "import os,shutil; print(shutil.which('git'))"      → /data/service/hnp/bin/git
$ python3 -c "import os; os.posix_spawn('git',['git','--version'],os.environ)"
  FileNotFoundError: [Errno 2] No such file or directory: 'git'
$ python3 -c "import subprocess; print(subprocess.run(['/data/service/hnp/bin/git','--version'],capture_output=True,text=True).stdout)"
  git version 2.45.2                                              ← 绝对路径正常
```

Python 3.12 的 `subprocess` 默认走 `posix_spawn`（`subprocess._USE_POSIX_SPAWN = True`），
而 **OHOS 的 musl 实现不为 `posix_spawn` 做 PATH 搜索**（那是 `posix_spawnp` 的语义）。
结果：**绝对路径的调用正常，裸命令名的调用一律失败**。

**影响面**：所有用 `subprocess.run(["git"|"tar"|...])` 的技能模块在本机都会失败，而且多数是
**静默降级**——例如 `workflow_checks.check_pr_atomicity()` 的 `git` 调用失败后回退、
再失败就 `return 0`，于是 W2 在"没有提交"的工作树上永远输出 `✅ 无变更文件`（空检查）。
本次 `finish` 的 Step 9/10 就是这样被"绿灯"的，需按下面的显式检查复核。

**建议修复**：技能内所有 subprocess 调用改为经 `shutil.which()` 解析出的绝对路径，
或在模块入口 `subprocess._USE_POSIX_SPAWN = False`。

**本次采取的处置**：不改框架；用 `subprocess._USE_POSIX_SPAWN = False` 绕过后跑通官方
preflight（见 `preflight-check.log`），并用显式变更集独立完成 W2/原子性检查
（见 `pr-atomicity-check.log`）。

## 3. `finish` Step 8 `gen_summary` 渲染失败（与本包无关）

```
⚠️ gen_summary 失败: 'str' object has no attribute 'append'
```

定位：`scripts/ohc/summary.py::_parse_yaml_simple` 在扫描全仓 manifest 时崩溃，
触发文件为 **`archives/q/qpdf/12.3.2/manifest.yaml`** 与 `archives/q/qpdf/12.3.2.1/manifest.yaml`
（同一 key 既作标量又作列表）。逐文件扫描 11486 个 manifest，仅这 2 个失败：

```
扫描 manifest 数: 11486
失败数: 2
 - archives/q/qpdf/12.3.2.1/manifest.yaml AttributeError("'str' object has no attribute 'append'")
 - archives/q/qpdf/12.3.2/manifest.yaml   AttributeError("'str' object has no attribute 'append'")
```

因此 `SUMMARY.md` 未重新生成。修 qpdf 的 manifest 或给解析器加容错即可（均属框架/他包范畴，
本次不动）。

## 4. `finish` 全仓 JC 扫描命中他包遗留状态文件（阻塞 W3，需按 PR 范围扫描）

```
[FAIL] JC1: 3 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
       archives/k/kics/2.1.20/.staging-verified
```

这三处**在 `origin/main` 中就已被跟踪**（`git cat-file -e origin/main:<path>` 全部命中），
属他包历史遗留。本工作树无提交时 `junk_check.sh` 会从 `incremental`
（`git diff origin/main...HEAD`）退化为 `full`（`git ls-files` 全仓扫描），于是被历史债拦下。

**处置**：未删除他包文件（W2 原子性）；改用 CI 真实使用的 `prdiff` 模式
（`JUNK_PR_DIFF=<本 PR 变更集>`，与 buildbot `checkout-pr` 口径一致）复核：
`JC_RESULT=pass / JC_ERRORS=0 / 涉及软件数 1（合规）`，见 `junk-check-prdiff.log`。
