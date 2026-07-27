# c3c 0.8.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-11
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译策略

OHOS SDK 只提供 libc++，而 c3c 上游 `llvm-for-c3` 的 `linux-aarch64` 预编译 LLVM/lld 静态库依赖 GNU libstdc++ ABI。CI 链接时会出现 `std::__detail::_List_node_base::_M_hook/_M_unhook` 等 libstdc++ 符号未定义。

因此 Conan CI 包禁用 LLVM 后端，构建可运行的 c3c 前端命令，用于 `--version`/`--help` 等 smoke 验证：

```bash
cmake -DC3_WITH_LLVM=OFF \
  -DC3_FETCH_LLVM=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS="-DAVR_DISABLE -DARM_DISABLE -DRISCV_DISABLE -DWASM_DISABLE -DX86_DISABLE -Wno-error=switch" \
  -DCMAKE_CXX_FLAGS="-DAVR_DISABLE -DARM_DISABLE -DRISCV_DISABLE -DWASM_DISABLE -DX86_DISABLE"

cmake --build . -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LLVM 预编译包（linux-aarch64）链接失败 | 预编译 LLVM/lld 用 GCC/libstdc++ 编译，OHOS clang 工具链只提供 libc++ | CI 禁用 LLVM 后端，不拉取/链接该 artifact |
| 2 | 追加 `-lstdc++` 仍失败 | OHOS SDK 搜索路径中不存在 GNU libstdc++ | 不再使用依赖 GNU libstdc++ 的 artifact |
| 3 | c3c 默认后端为 LLVM | 无 LLVM 后端时不能执行 C3 代码生成测试 | 构建和 test_package 均运行上游 `c3c utest` 内置前端自测，并保留 `--version`/`--help` smoke |

## 上游测试范围

`c3c utest` 直接运行上游 `src/compiler_tests/tests.c`，覆盖 i128 运算、arena allocator 和 JSON parser，且不进入 LLVM 代码生成。完整 `scripts/tools/ci_tests.sh`、`test/test_suite/` 和 `test/unit/` 均需要 LLVM 后端，因此当前 OHOS 无后端构建不宣称运行这些测试。

## 后续完整后端方案

如需发布完整 LLVM 后端版本，需要先提供用 OHOS clang/libc++ 构建的 LLVM 19-23 + lld 依赖包，或将 LLVM/lld 作为独立 Conan 包发布后让 c3c `C3_FETCH_LLVM=OFF` 并通过 `CMAKE_PREFIX_PATH` 使用该依赖。
---

**编译结束**: 2026-07-22 17:37
**最终状态**: built
