# pex 1.20140409 Adaptation Notes

## W0: Dependency Check

`pex` has no Conan library dependency. Its runtime prerequisites are a POSIX
shell, `curl`, and `git`; PostgreSQL `pg_config` and `psql` are needed only by
commands that manage PostgreSQL extensions. The optional `audit` command also
needs Perl and the Perl `YAML` module.

The current Windows host has no Conan, Perl, `prove`, or `make` on `PATH`, and
WSL has no installed Linux distribution. These prerequisites are recorded for
the target shadow environment instead of being mixed into this package.

## Registry Duplicate Check

The configured `ohpcd` Conan registry was queried directly through its public
V2 API on 2026-09-11:

```text
GET https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/v2/conans/search?q=pex%2F%2A
HTTP 200
{"results":[]}
```

No `pex` recipe or version is published, so `pex/1.20140409` is not a
duplicate artifact. `origin/main` also has no prior `archives/p/pex` history,
and no remote branch named `pex` was found. The unrelated remote branch
`feat/alopex-4.0a` is a different package.

## W1/W2: Source and Recipe

The upstream project is `petere/pex` tag `1.20140409`. It is a pure shell
application with an install-only Makefile. The recipe fetches the verified
GitHub codeload tarball, installs `pex`, its manual page, documentation, and
license, and registers the CLI through the software-level `commands.json`.

The upstream project has no C/C++ unit-test suite and no separately organized
integration-test suite. Its 17 POSIX shell TAP files under `t/*.t` contain 98
planned assertions when the optional Perl/YAML-backed `audit.t` suite is
available. Linux uses `make check`; OHOS uses
`prove --exec /system/bin/sh t/*.t`. The OHOS package copy changes the
installed script shebang from `#!/bin/sh` to `#!/system/bin/sh`, adds the
runtime mode-bit guard, and applies the narrowly scoped TAP skip only in the
ephemeral OHOS build copy when the filesystem cannot remove read bits.

## Local Verification

- Python AST and JSON syntax: passed.
- YAML parsing for all manifests: passed.
- Git Bash shell syntax check: passed.
- Consumer shell test against a package-layout copy: 15/15 passed.
- Conan create and official upstream TAP suite: not run locally because Conan,
  Perl, `prove`, and `make` are unavailable on this host.
- Shadow CI results (#43625, #43670, #43815, #43866, and current branch-bound
  #43900, manually triggered by the PR comment `/rebuild`): #43900 passed
  Conan `test_package`, L0, L1, recipe export, source download, build/test,
  and cleanup on `OpenHarmonyPCDeveloper-CI-020`. The current evidence remains
  17 planned TAP files and 98 planned assertions; the CI image executes 16
  files and 88 assertions, with 10 `audit.t` assertions skipped because Perl
  YAML is unavailable and one `pg_config.t` permission-precondition assertion
  conditionally skipped because OHOS retained read mode bits after `chmod a-r`.
  The other 87 executable assertions pass, and the separate consumer test is
  15/15. #43866 is retained as a historical failure only: its exported recipe
  was the old mode-guard-only revision (`build()` line 79), not current
  `b795d9544c`, so it cannot be used to reject the current fix.
- Real device: not run in this round. Shadow CI was run and is recorded above.

## Handoff

Next target-environment command:

```text
conan create archives/p/pex/1.20140409 --build=missing
```

For the repository W3 shadow CI, run:

```text
zsh ci/conan/build_and_test.sh archives/p/pex/1.20140409
```

For a queued device W5 run, first check connectivity:

```text
ssh -i C:\Users\ASUS\.ssh\ohos_pc_codex_ed25519 -p 2222 -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes currentUser@<device-ip> "echo ok"
```

Then create and run the isolated job:

```text
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" --user codex --job pex-1.20140409-<timestamp> --package archives/p/pex/1.20140409 --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
sh "$HOME/ohos-users/codex/pex-1.20140409-<timestamp>/run-conan-heavy.sh"
```

Use the OHOS Conan profile and an environment that provides
`/system/bin/sh`, `curl`, `git`, `make`, and `prove`. After a successful
consumer test, run the single-package shadow CI command used by the
repository and perform one queued real-device smoke test for `pex --help`,
`pex --cache`, and `pex --repository`.

## Final Status

前置适配完成；版本目录和 test_package 已准备好。当前分支已由 #43900
复验通过，当前版本仍保持发布待定状态；制品仓查询在 2026-09-11 仍为
`results=[]`，所以不能宣称已发布。真机验证仍待目标环境执行。Issue
编号按本轮指令不再处理。

## Path B Knowledge-Draft Candidates

本 PR 追加 4 组与 `pex/1.20140409` 直接相关的知识草稿配对文件，作为
路径 B（贡献创新）申请材料：

1. `DRAFT-pex-1.20140409-ohos-shell-entrypoint`
   （纯 POSIX shell 应用在 OHOS 上需要同时修正测试入口与安装后 shebang）：
   记录 `/bin/sh` 到 `/system/bin/sh` 的测试入口与安装后 CLI shebang
   两阶段边界。
2. `DRAFT-pex-1.20140409-tap-evidence-boundary`
   （pex 的上游测试必须按 shell TAP 真实入口统计，不能把单元测试和集成测试分类为 0/0 通过）：
   解释单元测试/集成测试分类为 0 的真实原因，并记录 17 个上游 TAP
   文件、98 个计划断言、CI 实际 16/88 的统计边界。
3. `DRAFT-pex-1.20140409-permission-semantics`
   （pex pg_config.t 的不可读 postmaster.opts 断言暴露 OHOS 与上游 POSIX 权限语义差异）：
   记录 `t/pg_config.t` 第 7 项不可读 `postmaster.opts` 断言在 OHOS
   CI 失败的事实、复现顺序，以及当 `chmod a-r` 未改变模式位时只跳过
   该断言的处理边界。
4. `DRAFT-pex-1.20140409-consumer-package-contract`
   （pex 的 Conan 消费者契约必须与上游 TAP 套件分开复核）：
   记录安装后文件布局、OHOS shebang、XDG 路径、Git 仓库操作和错误
   诊断的 15 项消费者断言，以及它们与上游 98 项 TAP 断言的独立统计口径。

草稿均保留 `draft: true`，不预占正式 E 编号，也不声称已获 B 类认定；
最终分类由知识库维护者和赛事评审决定。

## 结束标记

前置适配和本机提交自检阶段结束；当前分支 `b795d9544c` 已由 shadow CI
#43900 复验通过，消费者测试 15/15，制品仓截至 2026-09-11 仍无
`pex/1.20140409`。条件 TAP skip 修复已验证，真机测试和后续发布仍未完成。
