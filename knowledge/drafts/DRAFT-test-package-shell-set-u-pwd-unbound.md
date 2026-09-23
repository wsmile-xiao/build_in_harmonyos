# DRAFT-test-package-shell-set-u-pwd-unbound — test_package shell 脚本 set -u 下 $PWD unbound

> **Contributor**: codex | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: ohos / test_package / shell / hmdfs
> **Audience**: 所有在 OHOS 上由 `conan test()` 以 bash 包装执行、且脚本 `set -u` 并裸引用 `$PWD` 的 test_package 脚本

## 触发（trigger）

- test_package 的 `test.sh` 声明 `set -eu`，临时目录用 `${TMPDIR:-$PWD}/xxx-$$`。
- conan `test()` 以 `/data/service/hnp/bin/bash test.sh <bin-dir>` 执行，报 `PWD: unbound variable`（`set -u` 命中），`test()` 整体 exit 1。

## 机制（root cause）

- 根因与 `DRAFT-ohos-autotools-configure-re-exec-cwd-env` 相同：OHOS 上 bash 启动时 `getcwd()` 在 HMDFS 父目录链失败（EPERM），进程环境无 `PWD` → `$PWD` 未绑定。
- 差异在**触发面**：这里是 test.sh 脚本自身的 `$PWD` 裸引用（非 autotools configure 重执行），因此修复应落在脚本内，而非配方 `os.environ` 预置。
- 诊断噪声：`shell-init: error retrieving current directory` / `job-working-directory: ... getcwd: cannot access parent directories`。

## 修复（rec）

```bash
# test.sh 内，避免裸引用 $PWD
workdir="${TMPDIR:-${HOME:-/data/service/hnp}}/rgbds-test-$$"
```

`$HOME` 在 `conanrun` 环境内可用且可写；用 `:-` 链式 fallback 保证 `set -u` 下不再 unbound。

## 注意

- 不要误判为「测试断言失败」—— 报错发生在 `workdir=` 这一行，与断言无关；先看错误行号定位到环境变量。
- 备选方案：在 `test_package/conanfile.py` 的 `test()` 里 `os.environ["PWD"] = <目录>` 预置 PWD（同 configure 场景），但脚本内改 fallback 更自包含。

## 查重（dedup）

- `grep -rl "PWD: unbound\|unbound variable" knowledge/` → 无同签名条目。
- 最相近：`DRAFT-ohos-autotools-configure-re-exec-cwd-env`（configure re-exec 触发 + `os.environ["PWD"]` 修复，触发面/修复面均不同）、`E330-draft-2301`（测试 runner 的 shell 能力探测）。

## Source

- Package: `archives/r/rgbds/1.0.1`（test_package/test_rgbds.sh line 21）
- 真机验证：rgbds/1.0.1 shadow CI，job `rgbds-1.0.1-shadow-20260920-144737`，修复后 test_package 8/8 断言通过
