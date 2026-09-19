# Odin

Odin 是一种通用编程语言，具有独特类型系统，专为高性能、现代系统和面向数据编程而设计。
本适配将 Odin 编译器（dev-2026-08 版本）构建到 HarmonyOS PC（aarch64-linux-ohos）平台。

## 特性
- 编译器本体为 C++（`src/main.cpp` unity build + `src/libtommath.cpp`），依赖 LLVM 的 C++ API 生成机器码。
- 运行时库：`base/`（builtin/runtime/intrinsics）+ `core/`（标准库）+ `shared/`（共享实现）+ `vendor/`（第三方绑定）。
- 默认目标架构 AArch64（对应制品仓 LLVM 22.1.0 的 AArch64 后端）。

## 构建要点
- 依赖：`llvm/22.1.0`（制品仓已发布，shared 聚合库 `libLLVM-22.so`）。
- 上游 `build_odin.sh` 的 `uname -s` 分支不支持 `HarmonyOS`，配方内显式构造 Linux 分支等价编译命令并适配聚合库链接。
- 非 git 构建时显式注入 `-DODIN_VERSION_RAW="dev-2026-08"` 对齐登记版本。

## 版本
- dev-2026-08（tag `8412dc37aa91def0c2fa90f89eade29056b4e608`，2026-08-06 发布）
