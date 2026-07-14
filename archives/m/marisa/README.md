# marisa

## 简介
MARISA（Matching Algorithm with Recursively Implemented StorAge）是一种静态、
空间高效的前缀树（trie）数据结构。libmarisa 是其 C++ 库实现，提供键集
（Keyset）、前缀树（Trie）与代理（Agent）等接口，支持 lookup /
common-prefix-search / predictive-search / reverse-lookup 等查询。

## OHOS 适配
- 使用 CMake 构建（项目要求 cmake ≥ 3.22）
- 仅产出静态库 libmarisa.a（`BUILD_SHARED_LIBS=OFF`）
- 关闭 CLI 工具（`ENABLE_TOOLS=OFF`），保持库包纯净
- 关闭原生 SIMD（`ENABLE_NATIVE_CODE=OFF`），避免 worker 指令集差异
- 上游自带 5 个单元测试，在 build() 中通过 ctest 运行
- C++20：上游 CMakeLists 显式声明，clang 15 支持，无需补丁

## 依赖
无外部依赖，仅依赖 C++ 标准库。

## 功能验证
```bash
c++ -std=c++20 -o test_marisa test_marisa.cpp \
    -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmarisa
./test_marisa
```

## 参考
- 官网: https://github.com/s-yata/marisa-trie
