# sml 1.1.11 适配笔记

## 编译环境
- 构建系统: cmake (header-only library, 无编译产物)
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: published（conan-verify 8 门禁全部通过）

## 编译步骤

```bash
# 上游源码（官方 GitHub tag v1.1.11）
curl -L -o sml-1.1.11.tar.gz https://github.com/boost-ext/sml/archive/refs/tags/v1.1.11.tar.gz
# SHA-256: 8773efd639ce9649dc449135c8c53232e1cb5f4037d44be02c1b9ccc343f246d

# 本地全量上游测试（OHOS aarch64 工具链, CMake + ctest 规范路径）
cmake -S . -B build -DSML_BUILD_TESTS=ON -DSML_BUILD_EXAMPLES=OFF -DSML_BUILD_BENCHMARKS=OFF
cmake --build build -j2
ctest --test-dir build --output-on-failure   # 30/30 通过

# Conan 配方验证（conan-verify：G0-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify sml 1.1.11
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 主页与 archive 直连超时（网络限制） | 执行机仅 codeload/ghfast 镜像可达 | 用官方 codeload/ghfast 镜像下载 tarball；conandata.yml 仍保留官方 GitHub URL（R39），校验 sha256 一致（8773efd6…） |
| 2 | `make test` 对 clang++ 固定加 `-fno-exceptions` 导致 actions_defer 编译失败 | 上游 Makefile 为 GCC/clang 统一关闭异常，但静态队列测试依赖 throw | 改用上游 CI 同源的 CMake 路径（SML_USE_EXCEPTIONS 默认 ON）跑 ctest，30/30 全过；Makefile 路径不作为测试依据 |
| 3 | init-build 默认模板生成 autotools 版骨架 | 模板按 URL 猜测构建系统 | 重写 conanfile.py 为 header-only / CMake 版，package_type=header-library |
| 4 | test_package 需真实调用 API（R34） | 模板空壳不满足 | 重写为 C++14 消费者测试：定义事件/状态/迁移表 → 驱动状态机 → 断言 locked→unlocked→locked |

## 源码修改

无（纯 header-only 库，未修改任何上游源文件；未使用平台宏补丁）

## 依赖版本

- 无运行时依赖（header-only，仅依赖 C++14 标准库）
- 测试环境: clang 15.0.4 / cmake 4.1.2 / conan 2.29.1

## 验证结果

```bash
# 上游测试: ctest 30/30 通过 (ft 功能 + ut 工具 + unit 单元)
# 消费者验证: conan create 内 test_package 编译运行通过 (test_sml PASSED)
# 产物: header-library (include/boost/sml.hpp + include/boost/sml/)

# 测试统计 (R51 申报)
# - ctest 注册 30 项, 实测运行 30 项, 通过 30 项, 通过率 100%
# - test/ft/errors/ 4 项为预期编译失败测试 (未注册 ctest, Makefile 目标验证)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 1.8KB | header-only 配方 (package_type=header-library) |
| conandata.yml | 0.3KB | 官方源 URL + SHA-256 |
| test_package/ | 4 文件 | 消费者测试 (CMakeDeps + test.cpp 状态机断言) |

## 注意事项

- header-only 库，无 .so/.a 产物，无需 commands.json（R38 仅命令行工具需要）
- 上游 Makefile 的 `-fno-exceptions` 与 CMake 默认不一致，测试以 CMake/ctest 为准
- 官方 tag 为 `v1.1.11`（非 `1.1.11`）
---

**编译结束**: 2026-09-08 01:25
**最终状态**: built
