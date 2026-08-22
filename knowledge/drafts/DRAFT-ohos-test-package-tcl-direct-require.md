# DRAFT-ohos-test-package-tcl-direct-require — test_package 直连 tcl + TCL_LIBRARY（OHOS）

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-08-21
> **Severity**: medium | **Category**: ohos / conan / packaging
> **Audience**: expect / dejagnu / tclsh 消费方，及所有依赖 Tcl/expect 运行时脚本工具的包

## Scope
依赖 Tcl/expect 的包在 OHOS 上写 test_package 时，需要直接 requires tcl 以解析其 package_folder，并在 test() 中设置 `TCL_LIBRARY` 指向 init.tcl，用 bash（而非 mksh）运行测试脚本。

## 背景
- Conan 只为**直接依赖**解析 package_folder。tcl 对 expect 是传递依赖，在 test_package 的 test() 生命周期里拿不到 tcl 包路径。
- OHOS 上 expect 运行需要 `TCL_LIBRARY` 指向 tcl 的 `lib/tcl8.6/init.tcl`；缺则 `expect -v` 报 `Tcl_Init failed: Can't find a usable init.tcl`。
- OHOS `/system/bin/sh` 是 mksh，无法可靠执行 POSIX 测试脚本，须用 bash。

## 模式（步骤）
1. test_package `requirements()` 直接 `self.requires("tcl/8.6.14")`。
2. `test()` 中 `self.dependencies["tcl"].package_folder` → `TCL_LIBRARY=<tcl>/lib/tcl8.6`。
3. 用 bash（`CONFIG_SHELL` 或显式 `/data/service/hnp/bin/bash`）执行 test.sh，命令在 conanrun 环境运行。

## 验证
- `RUN: TCL_LIBRARY=<tcl>/lib/tcl8.6 bash test.sh` → `[ok] runtest is functional` + `[ok] dejagnu smoke test passed`（conan-create-round-4b.log line 409-413）。
- `expect -v` 正常输出 `expect version 5.45.4`。

## 禁止
- 不用 `/system/bin/sh`（mksh）跑测试脚本；不忽略 TCL_LIBRARY 直接跑 expect；不写死绝对路径的 TCL_LIBRARY（依赖缓存路径会变，不可移植）。

## Source
- Package: `archives/d/dejagnu/1.6.3/test_package/`（conanfile.py + test.sh）
- 证据日志（设备）：`conan-create-round-4b.log`
- Similar: E280（Tcl 静态构建 TCL_LIBRARY/TCLLIBPATH 相关）
