# epr-api 2.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

上游 epr-api 2.3 为 CMake 构建（根目录 CMakeLists.txt），raw makefile 使用 `ld -shared` 不适用 OHOS，采用 CMake 路径：

```bash
cmake -S . -B build-ohos \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DBUILD_TESTS=ON -DBUILD_STATIC_LIB=ON -DBUILD_DOCS=OFF \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-ohos -j4
ctest --test-dir build-ohos --output-on-failure   # 2/2 通过
cmake --install build-ohos                        # include/ + lib/libepr_api.{so,a}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 报错 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(2.8)`，本机 CMake 4.1 移除 <3.5 兼容 | 配置期加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（配方 generate() 中作为 cache_variables 固化） |
| 2 | init-build 下载 `https://github.com/bcdev/epr-api` 返回 HTML | `--url` 直接给仓库首页而非 tarball | 改用官方标签 tarball `https://github.com/bcdev/epr-api/archive/refs/tags/2.3.tar.gz` |
| 3 | conan-init 误判构建系统 autotools | URL 推断偏好 | 手工将配方改为 CMakeToolchain + CMake 驱动（参考 abcmidi 配方） |

## 源码修改

无源码补丁（纯配方/构建系统适配）。

## 依赖版本

- 无第三方依赖（纯 C 库，仅链接系统 libm）。
- 工具链: clang 15.0.4 / make 4.4.1 / cmake 4.1.2 / conan 2.29.1

## 验证结果

```bash
$ ctest --test-dir build-ohos --output-on-failure
1/2 Test #1: TEST_EPR_03 ......... Passed
2/2 Test #2: BCCUNIT_TEST_SUITE_01 Passed
100% tests passed, 0 tests failed out of 2
```
---

**编译结束**: 2026-09-22 21:38
**最终状态**: published
