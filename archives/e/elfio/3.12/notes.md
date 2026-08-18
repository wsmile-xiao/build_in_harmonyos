# elfio 3.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-14
- 编译器: clang/clang++
- 状态: published

## 编译步骤

ELFIO 是 C++ header-only 库，使用 CMake 构建。release tarball 不含 tests/ 目录，
在 generate() 中禁用 examples 和 tests（`ELFIO_BUILD_EXAMPLES=False`、`ELFIO_BUILD_TESTS=False`）。

```bash
source .build-context-elfio-3.12 && cd $BUILD_SRC_DIR
cmake -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build
cmake --install build
```

安装产物：include/elfio/ 头文件 + CMake 配置文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 URL waterlan.home.xs4all.nl 已失效 | 站点重定向 | 改用 GitHub releases 官方源 |
| 2 | init-build 误判为 autotools | BUILD_SYSTEM 环境变量默认值 | 手动重写 conanfile.py 为 CMake 配方 |
| 3 | CMake add_subdirectory(tests) 失败 | release tarball 不含 tests/ | generate() 中 ELFIO_BUILD_TESTS=False |
| 4 | test_package 编译错误：ELFIO 常量需命名空间 | 未使用 ELFIO 命名空间 | 添加 using namespace ELFIO |
| 5 | L0d 门禁 stub_test_method 失败 | test() 缺少 self.run() | 改用 self.run() 直接执行测试 |
| 6 | /tmp 只读 (E002) | 平台限制 | 使用 $TMPDIR |

## 源码修改

无补丁。ELFIO 是 header-only 库，源码无需修改即可在鸿蒙 PC 平台编译。

## 依赖版本

无依赖。preflight 检查确认无依赖需要发布。

## 验证结果

```bash
# conan-verify 门禁（G0-G4 + L2/L4/L5 全 PASS）
$ python3 ./scripts/ohc-run.py conan-verify elfio 3.12
# → All gates PASS

# 独立 conan create（干净缓存）
$ conan create archives/e/elfio/3.12/conanfile.py --name=elfio --version=3.12 \
    -pr=ci/conan/profiles/ohos-aarch64 -s build_type=Release
# → elfio/3.12 (test package): RUN: ./test_elfio
# → ELFIO version: 3.12
# → All ELFIO API tests passed!
```

## 注意事项

- ELFIO 是 header-only 库，package_type 为 "header-library"，无编译产物
- conandata.yml URL 指向 GitHub 官方 releases 源，CI 自动添加 gh-proxy 镜像 fallback
---

**编译结束**: 2026-08-14 13:01
**最终状态**: published
