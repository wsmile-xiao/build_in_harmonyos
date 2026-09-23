# E2163-draft — perl Configure 在 OHOS 上要显式关掉 prctl / IPC SysV 误探测

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-09-08
> **Severity**: 🟡 medium | **Category**: perl / configure / ohos / runtime

## Usage

当 Perl `Configure` 在 OHOS 上误判 `prctl(PR_SET_NAME)`、`IPC/SysV`、`langinfo` 之类能力时，后续上游测试会出现 `$0`/进程名异常、挂起或平台语义失败。

## Scope

- `perl/5.42.2.1` 的 `Configure` 阶段。
- 上游 `make test_harness_notty` 中依赖进程名、信号、IPC 语义的用例。
- 需要 copy-based link wrapper、可写 `TMPDIR` 和 `TMPPREFIX` 的宿主构建。

## Symptom

```
op/leaky-magic.t hangs
op/lex.t fails around $0 / prctl
op/taint.t hangs
lib/warnings.t hangs or fails
Symbolic links are NOT supported
```

## Fix

在 OHOS native 配置里显式传入：

```sh
-Ui_langinfo -Ud_nl_langinfo -Ud_nl_langinfo_l
-Ud_prctl -Ud_prctl_set_name
-Dnoextensions=GDBM_File NDBM_File ODBM_File DB_File IPC/SysV
```

同时保留 OHOS 的 copy-based link wrapper、`SHELL=/bin/sh`、`CONFIG_SHELL=/bin/sh`、
`TMPDIR` 和 `TMPPREFIX`。

## Gotchas

- `prctl()` 可能“看起来可用”，但 `PR_SET_NAME` 语义不适合 Perl 的 `$0` 逻辑。
- `IPC/SysV` 不要留给上游自动探测，它会把测试链路带进不稳定分支。
- 这类配置修补属于构建期前置条件，不是 test_package 里临时补丁。
