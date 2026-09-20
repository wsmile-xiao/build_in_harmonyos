# ols

`ols` 是 Odin 语言官方语言服务器（Language Server Protocol 实现），提供补全、
跳转定义/类型定义、悬停文档、引用查找、重命名、签名帮助、文档符号、语义高亮、
inlay hints、代码动作、格式化等能力。本适配将其构建到 HarmonyOS PC
（aarch64-linux-ohos）平台。

## 特性
- 纯 Odin 语言实现，产物为单一可执行文件 `bin/ols`，无运行期动态库依赖
  （`DT_NEEDED` 仅 `libc.so`，`RUNPATH=$ORIGIN`）。
- 传输层为 stdio 上的标准 LSP JSON-RPC（`Content-Length` + CRLF 分帧）。
- 附带运行期资产 `bin/builtin/`（`builtin.odin`、`intrinsics.odin`）：上游要求
  该目录位于 `ols` 二进制同级，用于解析 Odin 内置过程与类型的类型签名。

## 构建要点
- 构建工具链：`odin` 编译器（`tool_requires`，`odin/dev-2026-08`）+ `llvm/22.1.0`
  （odin 运行期解析 `libLLVM.so.22.1`）。
- 上游构建完全由 odin 驱动（`build.sh` / `ci.sh`），无 CMake/Make；本适配取上游
  CI 形态命令：`odin build src/ -show-timings -collection:src=src -out:ols
  -no-bounds-check -o:speed -define:VERSION=dev-2026-06`。
- 平台垫片（0 补丁）：OHOS libc 未导出线程取消符号（`pthread_setcancelstate` 等），
  `ols` 经 `core:thread` 创建请求线程会链接失败；配方在构建期生成无害空桩并以
  `-extra-linker-flags` 注入链接，不修改上游任何源码。

## 版本
- dev-2026-06（上游 `DanielGavin/ols` tag `dev-2026-06`，
  commit `fa36fac9770c1715c33c13755bd4090b1959159f`）
