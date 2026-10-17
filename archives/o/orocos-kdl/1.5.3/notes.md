# orocos-kdl 1.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```bash
# 执行前显式设置路径；鸿蒙环境请使用可写的 TMPDIR，不要使用 /tmp。
: "${DEFAULT_PREFIX:?请设置 DEFAULT_PREFIX，例如 /storage/Users/currentUser/usr/local}"
: "${TEST_PREFIX:?请设置 TEST_PREFIX，例如 /storage/Users/currentUser/tmp/test-prefix}"
: "${TMPDIR:?请设置可写的 TMPDIR}"

# 1. 安装依赖 Eigen3
# Eigen3 为 header-only 库，从与 conandata.yml 一致的官方 GitLab 源下载并校验 sha256。
EIGEN_ARCHIVE="$TMPDIR/eigen-3.4.0.tar.gz"
curl -fsSL -o "$EIGEN_ARCHIVE" https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
echo "8586084f71f9bde545ee7fa6d00288b264a2b7ac3607b974e54d13e7162c1c72  $EIGEN_ARCHIVE" | sha256sum -c -
mkdir -p "$DEFAULT_PREFIX/include/eigen3"
tar -xzf "$EIGEN_ARCHIVE" --strip-components=1 -C "$DEFAULT_PREFIX/include/eigen3"

# 2. CMake 配置
cmake -B build -S . \
  -DCMAKE_INSTALL_PREFIX="$DEFAULT_PREFIX" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DEIGEN3_INCLUDE_DIR="$DEFAULT_PREFIX/include/eigen3"

# 3. 编译
cmake --build build -j2

# 4. 安装
cmake --install build --prefix "$TEST_PREFIX$DEFAULT_PREFIX"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | monorepo 结构，源码在 orocos_kdl 子目录 | GitHub 仓库包含多个子项目（orocos_kdl、kdl_parser 等） | init-build 自动检测嵌套源码并提升到顶层；conan recipe 中 configure 使用 build_script_folder="orocos_kdl" |
| 2 | 依赖 Eigen3 未安装 | header-only 线性代数库，非系统默认包含 | 从官方 GitLab 源下载 Eigen3 3.4.0，并以 conandata.yml 中的 sha256 校验 |
| 3 | /tmp 只读文件系统 | 鸿蒙平台限制 | 使用 $TMPDIR 环境变量路径 |

## 源码修改

对上游源码的兼容性修改全部在 conanfile.py 的 build() 阶段内联注入（无需单独补丁文件，
保证配方可复现）：

1. **`orocos_kdl/tests/kinfamtest.cpp`**：注入 `#include <cstdint>` 和
   `using uint = unsigned int;`。
   - 原因：上游测试使用 BSD `uint` 类型；HarmonyOS 的 C++17 libc++ 不默认声明该类型。
2. **`orocos_kdl/tests/framestest.cpp`**：注释掉 5 个硬编码 x86_64 的
   `std::hash<...>` 断言（如 `3450679443808348711u`）。
   - 原因：aarch64 libc++ 的 `std::hash` 实现不同，产生不同的但有效的哈希值；
     这些断言与 KDL 功能无关，注释后保留同文件内其余功能断言。

上述修改仅作用于上游 cppunit 测试编译，不改变 orocos-kdl 库的对外 API 或运行时产物。

## 依赖版本

- Eigen3: 3.4.0 (header-only, 从官方 GitLab 源下载并通过 sha256 校验)
- cppunit: 1.15.1（仅构建阶段的上游测试依赖，从源码临时构建，不随最终包发布）

## 验证结果

```bash
# 编译验证
$ cmake --build build -j2
[100%] Built target orocos-kdl

# 安装验证
$ cmake --install build --prefix $TEST_PREFIX/$DEFAULT_PREFIX
-- Install configuration: "Release"
-- Installing: .../lib/liborocos-kdl.so
-- Installing: .../include/kdl/*.hpp
-- Installing: .../share/orocos_kdl/cmake/*.cmake

# 产物清单
- liborocos-kdl.so (共享库)
- include/kdl/*.hpp (C++ 头文件)
- lib/pkgconfig/orocos-kdl.pc (pkg-config)
- share/orocos_kdl/cmake/ (CMake 配置)
```

## 注意事项

- orocos-kdl 是 C++ 库，需要 C++17 编译
- Eigen3 为 header-only 依赖，无需编译
- 上游测试在 conanfile.py 的 build() 阶段启用（`ENABLE_TESTS=ON`）；cppunit 从源码临时构建后，通过 `ctest --output-on-failure` 执行全部 8 项上游测试
- cppunit 仅用于构建阶段测试，不随最终 orocos-kdl 包发布
- 属于库类型产物，无需 commands.json
---

**编译结束**: 2026-07-16 15:04
**最终状态**: built
