# include-what-you-use (IWYU)

Google 出品的 C/C++ `#include` 分析工具：基于 Clang 前端分析源文件的头文件依赖，
输出"应添加/应移除"的 include 建议，并配合官方 `fix_includes.py` 直接改写文件。
0.26 版本仅兼容 Clang 22（上游 CMakeLists 硬性约束）。

- 上游：https://github.com/include-what-you-use/include-what-you-use
- 构建：CMake（standalone 模式，find_package(LLVM/Clang CONFIG)）
- 依赖：制品仓 `clang/22.1.8`（LLVM/Clang 一体包：cmake config + libclang-cpp + resource dir）、
  `llvm/22.1.0`、`zlib/1.3.2`、`zstd/1.5.7`、`xz/5.8.3.1`、`libedit/20240808`、`z3/4.15.4`
- 测试：上游 ctest 227 条（1 gtest + 224 e2e + 2 py），OHOS 真机全量实测 223 通过 /
  1 合法跳过 / 3 标准库实现差异失败（98.2%）；test_package 消费者用例 C1-C3（5/5）

## OHOS 适配

- 平台模块：设备 `uname -s=HarmonyOS` 不在 LLVM 22 平台表 → `Platform/HarmonyOS.cmake`
  （`include(Platform/Linux)`）经 CMAKE_MODULE_PATH 注入；不设 CMAKE_SYSTEM_NAME
  保持 `CMAKE_CROSSCOMPILING=FALSE`（llvm/clang 配方同款先例）。
- IWYU standalone 需要 clang 包**真实** cmake config（CMakeDeps 合成版无
  AddLLVM/HandleLLVMOptions/clang-cpp 目标）→ `LLVM_DIR`/`Clang_DIR` 直指
  `clang` 包 `lib/cmake/{llvm,clang}`。
- builtin 头自包含：`IWYU_RESOURCE_RELATIVE_TO=iwyu` + `IWYU_RESOURCE_DIR=../lib/clang/22`，
  package() 把 clang 包 `lib/clang/22/include` 拷入本包；运行时 3 个 NEEDED .so
  （libclang-cpp/libLLVM/libc++_shared）一并捆绑入包内 `lib/` + `RUNPATH=$ORIGIN/../lib`。
- OHOS XPM：iwyu ELF 与捆绑 .so 均 objcopy 去 .codesign + binary-sign-tool 自签。
- 测试标准库头注入仅用 `-isystem` CLI flag（system 头分类；CPATH 类环境变量被 clang
  归为 user include 破坏 IWYU 归属，实测 25 条 e2e 失败）。
- 零源码修改：上游 tests/ 原样运行，patches/ 为空。

## References

- https://include-what-you-use.org
- https://github.com/include-what-you-use/include-what-you-use
