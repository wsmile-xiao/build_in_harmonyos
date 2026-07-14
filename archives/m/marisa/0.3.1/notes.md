# marisa 0.3.1 适配笔记

## 概述
MARISA（Matching Algorithm with Recursively Implemented StorAge）是静态、
空间高效的前缀树（trie）数据结构；libmarisa 是其 C++ 库实现。本适配仅交付
库与上游单元测试，CLI 工具（marisa-build 等）未启用。

## 编译环境
- 构建系统: cmake（项目要求 cmake ≥ 3.22）
- 编译日期: 2026-07-14
- 编译器: clang 15（OHOS 自带，libc++）
- 构建类型: Release
- 状态: built

## 源码
- 上游: https://github.com/s-yata/marisa-trie
- 源码包: v0.3.1 tag 的 GitHub archive（官方 codeload 源，符合 R39）
- sha256: 986ed5e2967435e3a3932a8c95980993ae5a196111e377721f0849cad4e807f3

## 构建配置
- `BUILD_SHARED_LIBS=OFF`：仅产出静态库 libmarisa.a
- `ENABLE_TOOLS=OFF`：不构建 marisa-* CLI 工具（保持库包纯净，无需 commands.json）
- `ENABLE_NATIVE_CODE=OFF`：关闭 `-march=native` 与 SSE/BMI 代码路径，避免 worker 指令集差异
- `BUILD_TESTING`（默认 ON）：构建上游 5 个测试可执行程序，由 `cmake.test()` 运行

## 编译步骤
```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
      -DENABLE_TOOLS=OFF -DENABLE_NATIVE_CODE=OFF
cmake --build build --parallel 1
ctest --test-dir build          # 上游官方测试
cmake --install build
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无 | 源码为纯 C++ 标准库实现，无 glibc/syscall/procfs 依赖 | 无需补丁 |

## C++ 标准说明
上游 CMakeLists.txt 显式 `set(CMAKE_CXX_STANDARD 20)`，覆盖 Conan profile
的 `compiler.cppstd=17`；clang 15 完整支持 C++20。test_package 的 CMakeLists
同样设置 C++20，保证消费侧与库头文件 ABI 一致。无需补丁。

## 源码修改
无补丁。conandata.yml `patches: {}`。

## 验证结果
- 上游测试 base-test / io-test / vector-test / trie-test / marisa-test 全部运行（ctest）
- test_package/test_marisa.cpp：构建 Keyset→Trie、save/load 往返、
  lookup / predictive_search / common_prefix_search / reverse_lookup，9 项断言

## 交付物
- lib/libmarisa.a — 静态库
- include/marisa.h、include/marisa/*.h — 公共头文件
- lib/cmake/Marisa/* — CMake 配置（由上游 install 生成）
- lib/pkgconfig/marisa.pc — pkg-config 文件

## 依赖
无外部依赖，仅依赖 C++ 标准库（libc++）。

## 注意事项
- 仅静态库；如需 CLI 工具可在后续版本以 `ENABLE_TOOLS=ON` 启用并补 commands.json
- aarch64 下未启用 SIMD 优化（ENABLE_NATIVE_CODE=OFF），功能不受影响
