# rapidfuzz-cpp 3.3.4 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE target, 无编译产物)
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published
- 上游版本: 3.3.4 (官方 release tarball, SHA-256 a0dd2ef361cac165e12076696e7c7e8d069a2908abd9599ad4bd190de33f9881)

## 编译步骤

rapidfuzz-cpp 为 header-only C++ 库，无需编译库本体：

```bash
# 上游测试构建与运行 (HarmonyOS arm64 主机)
cmake -S <src> -B build -DRAPIDFUZZ_BUILD_TESTING=ON \
    -DCatch2_DIR=<local-catch2-prefix>/lib/cmake/Catch2
cmake --build build -j4
ctest --test-dir build --output-on-failure   # 10/10 通过

# Conan 配方验证 (ohos-aarch64 profile)
conan create archives/r/rapidfuzz-cpp/3.3.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 (下载/HTTP 均超时) | 本机无法直连 github.com | 官方 tarball 经 gh-proxy.com 镜像下载, SHA-256 逐字节核验一致; conan-verify 内置 ghfast.top 镜像注入 (E017) |
| 2 | conan-init 生成 autotools 模板 | 模板按 URL 猜测构建系统, rapidfuzz-cpp 实为 CMake header-only | 重写 conanfile.py: package_type=header-library, 直接拷贝 *.hpp/*.impl 头文件 |
| 3 | test_package 编译失败 `no member named 'distance' in namespace 'rapidfuzz'` | distance 算法函数位于 rapidfuzz 顶层命名空间 (rapidfuzz::levenshtein_distance), 非 rapidfuzz::distance | 修正 test.cpp 命名空间引用 |
| 4 | 上游测试 FetchContent 拉取 Catch2 失败 (GitHub 不可达) | 测试 CMakeLists 用 FetchContent 从 github.com 获取 Catch2 | 本机已缓存 Catch2 2.13.9, 用本地 prefix 的 Catch2_DIR 供给 find_package |
| 5 | conan create 首次报 `settings.os.version` 未定义 | 相对路径 profile 解析异常 | 使用绝对路径 profile 文件 |

## 依赖版本
- Catch2 2.13.9 (本地验证仅; recipe 无 requires, test_package 无外部依赖)

## 验证结果
- 上游测试: 21 个独立 TEST_CASE, 10 个测试目标全部通过 (ctest 10/10)
- 消费者 test_package: fuzz::ratio/partial_ratio/token_set_ratio + levenshtein/hamming distance 断言通过
- conan-verify: G0-G4 + L2/L4/L5 全部通过, 可标记 published

## 注意事项
- distance 算法 API 在 rapidfuzz 顶层命名空间; 头文件路径 rapidfuzz/distance/Levenshtein.hpp 等
- 无系统同名库冲突 (header-only), 无 commands.json 需要
- 消费方需 C++11+ (test_package 用 C++17 编译验证)
---

**编译结束**: 2026-09-02 23:23
**最终状态**: published
