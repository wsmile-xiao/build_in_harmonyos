# DRAFT-duckdb-1.5.5-build-time-target-binary-platform-probe

> Contributor: ohos-farm | Status: Draft | Updated: 2026-09-17
> Source: duckdb 1.5.5 HarmonyOS PC 适配（PR #9852）
> 领域：cross-compile / build-system / platform-detection / abi

## 背景

duckdb 1.5.5 在 HarmonyOS PC（aarch64-linux-ohos）上交叉编译时，构建在平台探测处失败。
1.5.5 相对 1.2.0 新增了一个**构建期运行目标二进制**的平台探测，使交叉编译成为硬阻塞。

## 错误签名

```text
Exec format error / cannot execute binary file
（或 duckdb_platform_binary 相关的 custom command 失败）
```

## 根因

上游 `CMakeLists.txt:872-895`：未指定 `DUCKDB_EXPLICIT_PLATFORM` 时，构建
`duckdb_platform_binary` 并在 custom command 中**运行它**来得到平台字符串；
该二进制面向目标平台，构建主机无法执行。且该目标经
`extension/extension_build_tools.cmake:88-94`（`duckdb_local_extension_repo`，`ALL` 目标）
与 `:214`（每个 loadable extension）被 `add_dependencies` 引用，默认 `all` 路径即触发。

第二层：该变量同时被转定义为 `DUCKDB_CUSTOM_PLATFORM`，命中
`platform.hpp:38-39`，从而绕过 `platform.hpp:70-74` 的 legacy ABI `#error` ——
对 musl + libc++ 的 OHOS 尤其重要。

## 触发条件

构建期运行自产的目标平台可执行文件做探测 + 交叉编译 + 未设置显式覆盖变量。

## 修复方案

```python
tc.variables["DUCKDB_EXPLICIT_PLATFORM"] = "linux_arm64"
```

取值必须与探测程序本会算出的字符串一致（本例依 `platform.hpp:37-88`，aarch64 Linux 得 `linux_arm64`）。

## 验证

见 `.kv`：正向（构建通过且与推演值一致）、负控（不设置则失败）、ABI 分支（撤掉后 `#error` 复现）。

## 适用与反例

适用：所有用"运行目标二进制"做平台探测的构建系统在交叉编译下的场景。
反例：原生构建可正常执行探测程序，问题不出现。
