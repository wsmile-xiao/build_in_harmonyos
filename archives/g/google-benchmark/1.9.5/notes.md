# google-benchmark 1.9.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (LLVM) / clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
cmake -S . -B build-native -DCMAKE_BUILD_TYPE=Release \
  -DBENCHMARK_ENABLE_TESTING=OFF -DBENCHMARK_ENABLE_GTEST_TESTS=OFF \
  -DBENCHMARK_INSTALL_DOCS=OFF -DBENCHMARK_ENABLE_DOXYGEN=OFF \
  -DBENCHMARK_ENABLE_LTO=OFF -DBENCHMARK_ENABLE_WERROR=OFF \
  -DCMAKE_INSTALL_PREFIX=<TEST_PREFIX>
cmake --build build-native -j2
cmake --install build-native
```

产物：`libbenchmark.a`、`libbenchmark_main.a`（静态库）、`include/benchmark/{benchmark.h,export.h}`、
CMake config（`benchmark::benchmark`）与 pkg-config（`benchmark.pc`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed (env_unsupported) | 工具 `_detect_binding` 只认 pybind11/boost_python/Python_Additions/find_package(Python) 标记；google-benchmark 的 Python 绑定用 nanobind（bindings/python/google_benchmark/benchmark.cc），漏检 → 90% C++ 主体的库被判 mixed | 按协议附录 D.4-2 边界规则（绑定类包判 cpp、辅助脚本不算主体）：google-benchmark 主体 C++（81/90 文件，90%），nanobind 绑定属绑定类包，正确判定 cpp；继续 cpp 适配 |
| 2 | cmake "System is unknown to cmake ... Platform/HarmonyOS" | 设备上 CMake 无法识别 OHOS 平台名（警告，非致命） | 仅警告；CMake 仍按通用系统配置成功，Threads 检测通过（-pthread），静态库构建/安装成功 |
| 3 | PTHREAD_AFFINITY 检测失败 | 上游 cmake/pthread_affinity.cpp 探测在 OHOS 不被支持（CPU 亲和性依赖不受支持的系统调用） | 非致命；该能力仅在探测时为统计信息用，不影响 benchmark 库本身的计时/状态统计核心功能 |

## 源码修改

无（patches 为空；未修改上游任何源码或测试文件）。

## 依赖版本

- 无外部运行时依赖（Threads: 系统 pthread）
- 工具链: clang 15.0.4 / GNU Make 4.4.1 / CMake 4.1.2

## 验证结果

```bash
# 原生静态库构建 + 安装成功（libbenchmark.a / libbenchmark_main.a / include/benchmark/*.h / CMake config）
cmake --build build-native && cmake --install build-native  # exit 0
# 官方 tarball sha256 双端点一致:
# 9631341c82bac4a288bef951f8b26b41f69021794184ece969f8473977eaa340
# 官方 tag v1.9.5 → commit 192ef10025eb2c4cdd392bc502f0c852196baa48
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake 构建，library，静态库默认，无外部依赖） |
| conandata.yml | 官方源 URL + sha256（v1.9.5 tag） |
| test_package/ | Conan L1 消费测试（benchmark::benchmark + 真实 benchmark 运行） |
| manifest.yaml | 版本级元数据（cmake，source sha256） |

## 注意事项

- 上游 python 绑定（bindings/python）使用 nanobind，本配方只构建 C++ 库本体（BENCHMARK_ENABLE_TESTING=OFF / GTEST OFF），不构建 python 绑定。
- lang-preflight 工具对 nanobind 绑定库存在漏检缺陷（已记录在 manifest knowledge_gained；若后续其他库同样用 nanobind 绑定，可考虑扩展 _detect_binding 标记集）。
---

**编译结束**: 2026-09-08 00:52
**最终状态**: built
