# libenvpp 1.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. init-build（官方 tag v1.5.3 tarball）
python3 scripts/ohc-run.py init-build libenvpp 1.5.3 \
  --url=https://github.com/ph3at/libenvpp/archive/refs/tags/v1.5.3.tar.gz --auto

# 2. 语言预检
python3 scripts/ohc-run.py lang-preflight libenvpp 1.5.3 --src $BUILD_SRC_DIR

# 3. 手工验证（OHOS aarch64 工具链）
cmake -S . -B build \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_NATIVE/build/cmake/ohos.toolchain.cmake \
  -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib \
  -DLIBENVPP_TESTS=ON -DLIBENVPP_INSTALL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
./build/libenvpp_tests          # 81 test cases / 756 assertions 全过

# 4. conan-init / conan-verify（8 道门禁全过）
python3 scripts/ohc-run.py conan-init libenvpp 1.5.3
python3 scripts/ohc-run.py conan-verify libenvpp 1.5.3

# 5. finish
python3 scripts/ohc-run.py finish libenvpp 1.5.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 3 断言失败（char 解析 "a"/"A"/"a " 误抛异常） | aarch64 上 `char` 默认为 unsigned，触发 `construct_from_string` 中 `std::is_unsigned_v<T>` 复校验分支，把 char 当数字以 int64 重解析失败 | patch: 排除 `char`/`signed char`/`unsigned char`（0001-include-libenvpp-detail-parser.hpp.patch） |
| 2 | OHOS CMake 配置时 llvm-ar 归档失败（"Error running link command"） | CMakeToolchain 自动探测到 SDK 的 `CMAKE_RANLIB` 指向不存在的 `llvm-ranlib`，SDK 只提供 `llvm-ar`（`/data/service/hnp/bin/llvm-ranlib` 是到 llvm-ar 的软链） | 显式 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib` |
| 3 | 配方 G2 首次失败：`The git submodule external/fmt is missing` | 官方 tarball 中子模块占位为空；上游 CMake 要求 `LIBENVPP_USE_SYSTEM_DEPS=ON` 时走 `find_package(fmt)`，但配方 generate() 漏了 CMakeDeps | 配方补 `CMakeDeps` 生成器 + `LIBENVPP_USE_SYSTEM_DEPS=ON` |
| 4 | 配方 G2 test_package 阶段找不到 `fmt/format.h` | registry 的 fmt/11.1.3 CMakeDeps 未导出 include 目录 | 切换到本仓库已发布的 fmt/12.2.0 并声明 `transitive_headers=True`（与 mitama-cpp-result/mp-units 惯例一致） |

## 源码修改

- `patches/0001-include-libenvpp-detail-parser.hpp.patch`：parser.hpp `construct_from_string` 的 unsigned 复校验分支排除字符类型，修复 aarch64（char 默认 unsigned）下 char 变量解析误抛异常；上游 main 分支同样存在该问题，属通用可复用修复。

## 依赖版本

- fmt/12.2.0（registry 已发布；公开头 `<fmt/format.h>` 传递消费）
- Catch2 3.8.1（仅上游测试构建用，不进入制品）

## 验证结果

```bash
# 上游测试（手工构建，OHOS aarch64）
./build/libenvpp_tests
# All tests passed (756 assertions in 81 test cases)

# test_package 消费者测试（OHOS 工具链，注入环境变量后运行）
./ohos-test-libenvpp
# libenvpp 1.5.3 test_package: OK (NUM_THREADS=4, ENABLE_FOO=1)

# conan-verify 8 门禁
# G0-G4 + L2/L4/L5 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（fmt/12.2.0 传递头依赖） |
| conandata.yml | 官方源码 + sha256 + 补丁声明 |
| patches/0001-include-libenvpp-detail-parser.hpp.patch | aarch64 char 解析修复 |
| test_package/ | 真实 API 消费者测试（R34） |
| reports/conan-verify-report.md | 验证报告 |

## 注意事项

- 上游 tarball 子模块为空占位，CI 构建依赖 registry 的 fmt 提供头文件；不得依赖 git submodule 网络拉取。
- `LIBENVPP_INSTALL` 必须为 ON 才安装 libenvpp 自身（默认 OFF）。
- W0b 历史核验：本库无历史归档（R01），不适用。
---

**编译结束**: 2026-09-22 16:41
**最终状态**: built
