# libkdtree 0.7.5 适配笔记

## 编译环境
- 构建系统: cmake（上游同时提供 autotools；配方统一走 CMake）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4 / clang++ 15.0.4（OHOS hnp 工具链，target aarch64-linux-ohos）
- 平台: HarmonyOS PC (aarch64)，profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 软件类型与依赖
- libkdtree++ 是 **header-only** 模板库：源码 `kdtree++/` 下 6 个头文件即全部产物，自身不编译
  任何 .a/.so。
- **零第三方依赖**：仅使用 C++ 标准库。`configure.ac` 的 `AC_CHECK_LIB` 段为空；
  `conanfile.py` 的 `requirements()` 无任何 `self.requires()`。
- 可选 `python-bindings/`（SWIG + PythonLibs）上游默认关闭，配方显式
  `BUILD_PYTHON_BINDINGS=OFF`。
- 因此**依赖前置核验（W0/R36）无待验证项**：`conan download` 对照探测确认制品仓当前
  无 `libkdtree/0.7.5` 配方（预期，本次即为其首次适配），且本包不 require 任何已发布包。

## 编译步骤

### 1. 上游 examples 真实构建（探索阶段，真机）

```bash
export PATH=/data/service/hnp/bin:$PATH
SRC=$TMPDIR/builds/libkdtree-0.7.5.work
cmake -S "$SRC" -B "$TMPDIR/libkdtree-build" -G Ninja \
      -DCMAKE_BUILD_TYPE=Release -DBUILD_PYTHON_BINDINGS=OFF \
      -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build "$TMPDIR/libkdtree-build"
# configure exit 0 / build exit 0，产物：
#   examples/test_kdtree, examples/test_hayne, examples/test_find_within_range
```

日志：`reports/native-cmake-configure.log`、`reports/native-cmake-build.log`。

CMake 4.1.2 对 `cmake_minimum_required(VERSION 3.5)` 只给弃用告警（v0.7.5 的 release
说明正是「Bump CMake minimum version to 3.5」以免被新版 CMake 拒绝），配置与构建均通过。

### 2. 上游测试实际运行（真机）

```bash
examples/test_kdtree              # exit 0，283 行输出
examples/test_hayne               # exit 0，1021 行输出
examples/test_find_within_range   # exit 0（设计为静默通过，仅 assert 判定）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 示例程序运行报 `Error loading shared library libc++_shared.so` | 本机执行环境继承了被污染的 `LD_LIBRARY_PATH`，其中 `/data/storage/el1/bundle/libs/arm64` 一项会让 OHOS 加载器直接解析失败（清空或只保留 `/system/lib64` 即恢复） | 运行/构建命令前显式 `export LD_LIBRARY_PATH=/system/lib64`；这是本机 shell 环境问题，与包本身无关（二进制仅 NEEDED `libc++_shared.so`/`libc.so`，系统自带） |
| 2 | `cmake.install()` 会把 6 个头文件平铺到 `include/` 根下 | 上游 CMakeLists 用 `install(FILES ${KDTREE_HEADERS} DESTINATION ${CMAKE_INSTALL_PREFIX}/include)`（绝对 DESTINATION，不经过 `CMAKE_INSTALL_INCLUDEDIR`） | 配方不调用 `cmake.install()`，在 `package()` 中按 autotools 的 `nobase_include_HEADERS` 语义 `copy("*.hpp", ... -> include/kdtree++/)` |
| 3 | CMake 报 `System is unknown to cmake, create: Platform/HarmonyOS` | 本机 CMake 4.1.2 未内置 HarmonyOS 平台描述文件 | 仅告警不阻塞；经 conan 的 CMakeToolchain（OHOS 适配版 conan 自动映射 `CMAKE_SYSTEM_NAME=HarmonyOS`）走 CI/W3 时同样正常 |

## 源码修改

无。`conandata.yml` 的 `patches` 为空，未引入任何 `__OHOS__` 平台宏或平台条件编译。

## 依赖版本

- 无第三方依赖（header-only，仅 C++ 标准库）。
- 构建期工具：CMake 4.1.2、Ninja 1.13.1（本机探索）／CI 使用 `ci/conan/build_and_test.sh`
  默认工具。

## 验证结果

```bash
# 上游测试（真机 aarch64-linux-ohos，3/3）
$ examples/test_kdtree && examples/test_hayne && examples/test_find_within_range
exit 0 / exit 0 / exit 0        # 日志见 reports/upstream-test_*.log

# 消费者测试（test_package，15 处 assert）
$ clang++ -std=c++11 -I<src> test_libkdtree.cpp -o test_libkdtree && ./test_libkdtree
libkdtree++ 0.7.5 consumer checks passed (2 nodes)
```

## 注意事项

- 本包为 header-only，`package()` 只产出 `include/kdtree++/` 与 `licenses/COPYING`，
  没有 `lib/`、`bin/`；`cpp_info.libdirs`/`bindirs` 已显式置空。
- 因此本包不需要 `commands.json`（R38：仅命令行工具需要）。
- 消费者必须使用 `#include <kdtree++/...>`，头文件已装在 `include/kdtree++/` 下
  （不要按上游 CMake 的平铺布局找头文件）。
---

**编译结束**: 2026-09-14 01:58
**最终状态**: built
