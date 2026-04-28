#!/bin/zsh
# Migration script for batch 3: c + d + e
set -e

BASE="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives"

### === ca-certificates ===
cat > "$BASE/c/ca-certificates/manifest.yaml" << 'YAML'
software: ca-certificates
display: "CA Certificates"
description: "Mozilla CA 证书捆绑包，提供受信任的根证书"
category: system
homepage: "https://salsa.debian.org/debian/ca-certificates"
license: MPL-2.0
build_system: custom

ohos_adaptation:
  key_points:
    - "纯数据包，无编译步骤"
    - "需要从 Mozilla certdata.txt 生成证书，或从 Debian 预编译包提取"
  common_dependencies: []

versions:
  "20250416":
    status: partial
    build_date: "2026-04-27"
YAML

cat > "$BASE/c/ca-certificates/README.md" << 'MD'
# ca-certificates

Mozilla CA 证书捆绑包，提供 HTTPS/TLS 连接所需的受信任根证书。

## 功能概述

- 提供 Mozilla 维护的受信任根 CA 证书集合
- 包含 update-ca-certificates 工具管理证书信任链
- 供 OpenSSL、GnuTLS 等 TLS 库使用

## OHOS 适配

- 纯数据包，无需编译
- 从 Debian 预编译包提取证书文件（certdata2pem.py 需要 Python cryptography 模块）
- 安装 150 个 Mozilla CA 证书到 `$PREFIX/share/ca-certificates/mozilla/`

## 依赖关系

- 无编译依赖
- Python cryptography 模块（可选，用于从源码生成证书）

## 参考资料

- Debian: https://salsa.debian.org/debian/ca-certificates
- Mozilla: https://www.mozilla.org/en-US/about/governance/policies/security-group/certs/
MD

cat > "$BASE/c/ca-certificates/20250416/manifest.yaml" << 'YAML'
version: "20250416"
status: partial
build_date: "2026-04-27"

source:
  url: "file:///storage/Users/currentUser/tmp/ca-certificates_20250419.tar.xz"
  tar_format: tar.xz

build:
  system: custom
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/ca-certificates/20250416/notes.md" << 'MD'
# ca-certificates 20250416 适配笔记

## 编译环境
- 构建系统: custom（纯数据包）
- 编译日期: 2026-04-27
- 编译器: N/A
- 状态: partial

## 编译步骤
ca-certificates 是纯数据包，不需要编译。证书文件需要从 Mozilla certdata.txt 生成。

由于缺少 Python cryptography 模块，无法运行 certdata2pem.py，因此从 Debian 预编译包提取了证书文件。

手动安装：
1. 创建目标目录 `share/ca-certificates/mozilla/`
2. 复制 150 个 Mozilla CA 证书文件
3. 复制 update-ca-certificates 工具和手册页

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | certdata2pem.py 无法运行 | 缺少 Python cryptography 模块 | 从 Debian 预编译包提取证书 |

## 依赖版本
无依赖

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ca-certificates-20250416-ohos-aarch64.tar.gz | 339.1KB | 主包 |
MD

rm -f "$BASE/c/ca-certificates/RELEASENOTE.md" "$BASE/c/ca-certificates/20250416/_meta.yaml" "$BASE/c/ca-certificates/20250416/PROGRESS.md" "$BASE/c/ca-certificates/20250416/README.md"
echo "ca-certificates done"

### === ccache ===
cat > "$BASE/c/ccache/manifest.yaml" << 'YAML'
software: ccache
display: "ccache"
description: "C/C++ 编译器缓存，加速重新编译"
category: build-tool
homepage: "https://ccache.dev/"
license: GPL-3.0-or-later
build_system: cmake

ohos_adaptation:
  key_points:
    - "需要更新 Makefile 和 configure 以支持 HarmonyOS"
  common_dependencies: []

versions:
  "4.12.1":
    status: partial
    build_date: "2026-04-17"
YAML

cat > "$BASE/c/ccache/README.md" << 'MD'
# ccache

ccache 是一个 C/C++ 编译器缓存工具，通过缓存编译结果来加速重新编译。

## 功能概述

- 缓存 C/C++ 编译结果，避免重复编译
- 透明集成，可作为编译器包装器使用
- 支持多种编译器（GCC、Clang、MSVC）
- 统计信息查看和缓存管理

## OHOS 适配

- 构建系统为 cmake，需要 2 个平台适配补丁
- 补丁 0001: Makefile 适配
- 补丁 0002: configure 脚本适配

## 依赖关系

- C++ 编译器
- CMake（构建工具）

## 参考资料

- 官网: https://ccache.dev/
- 源码: https://github.com/ccache/ccache
MD

cat > "$BASE/c/ccache/4.12.1/manifest.yaml" << 'YAML'
version: "4.12.1"
status: partial
build_date: "2026-04-17"

source:
  url: "https://github.com/ccache/ccache/archive/refs/tags/v4.12.1.tar.gz"
  tar_format: tar.gz

build:
  system: cmake
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied:
  - "0001-Makefile.patch"
  - "0002-configure.patch"

knowledge_gained: []
YAML

cat > "$BASE/c/ccache/4.12.1/notes.md" << 'MD'
# ccache 4.12.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-17
- 编译器: clang/clang++
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/ccache/RELEASENOTE.md" "$BASE/c/ccache/4.12.1/_meta.yaml" "$BASE/c/ccache/4.12.1/PROGRESS.md" "$BASE/c/ccache/4.12.1/README.md"
echo "ccache done"

### === check ===
cat > "$BASE/c/check/manifest.yaml" << 'YAML'
software: check
display: "Check"
description: "C 单元测试框架"
category: foundation
homepage: "https://libcheck.github.io/check/"
license: LGPL-2.1
build_system: autotools

ohos_adaptation:
  key_points:
    - "需要更新 config.guess/config.sub 以支持 HarmonyOS"
  common_dependencies: []

versions:
  "0.15.2":
    status: partial
    build_date: "2026-04-27"
YAML

cat > "$BASE/c/check/README.md" << 'MD'
# Check

Check 是一个 C 语言的单元测试框架，支持多种测试模式和自动检测内存泄漏。

## 功能概述

- 提供 C 单元测试框架
- 支持 Suite/TC/TCase 多层测试组织
- 自动检测内存泄漏
- 支持 fork 模式隔离测试
- 输出 XML/HTML/TAP 格式测试报告

## OHOS 适配

- 构建系统为 autotools，需要 2 个补丁（config.guess + config.sub）
- 用于其他 C 项目的单元测试

## 依赖关系

- C 编译器
- autotools 构建工具链

## 参考资料

- 官网: https://libcheck.github.io/check/
- 源码: https://github.com/libcheck/check
MD

cat > "$BASE/c/check/0.15.2/manifest.yaml" << 'YAML'
version: "0.15.2"
status: partial
build_date: "2026-04-27"

source:
  url: "https://github.com/libcheck/check/releases/download/0.15.2/check-0.15.2.tar.gz"
  tar_format: tar.gz

build:
  system: autotools
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied:
  - "0001-config.guess.patch"
  - "0002-config.sub.patch"

knowledge_gained: []
YAML

cat > "$BASE/c/check/0.15.2/notes.md" << 'MD'
# check 0.15.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/check/RELEASENOTE.md" "$BASE/c/check/0.15.2/_meta.yaml" "$BASE/c/check/0.15.2/PROGRESS.md" "$BASE/c/check/0.15.2/README.md"
echo "check done"

### === cjson ===
cat > "$BASE/c/cjson/manifest.yaml" << 'YAML'
software: cjson
display: "cJSON"
description: "ANSI C 语言实现的轻量级 JSON 解析器"
category: data
homepage: "https://github.com/DaveGamble/cJSON"
license: MIT
build_system: cmake

ohos_adaptation:
  key_points:
    - "需要 CMakeLists.txt 适配"
  common_dependencies: []

versions:
  "1.7.18":
    status: partial
    build_date: "2026-04-26"
YAML

cat > "$BASE/c/cjson/README.md" << 'MD'
# cJSON

cJSON 是一个 ANSI C 语言实现的超轻量级 JSON 解析器，只有一个 .c 文件和一个 .h 文件。

## 功能概述

- 解析和构建 JSON 数据
- 单文件实现，零外部依赖
- 支持 JSON 的所有标准类型
- 可选择启用打印格式化

## OHOS 适配

- 构建系统为 cmake，需要 1 个补丁（CMakeLists.txt 适配）

## 依赖关系

- ANSI C 编译器

## 参考资料

- 源码: https://github.com/DaveGamble/cJSON
MD

cat > "$BASE/c/cjson/1.7.18/manifest.yaml" << 'YAML'
version: "1.7.18"
status: partial
build_date: "2026-04-26"

source:
  url: "file:///storage/Users/currentUser/tmp/cjson-1.7.18.tar.gz"
  tar_format: tar.gz

build:
  system: cmake
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied:
  - "0001-CMakeLists.txt.patch"

knowledge_gained: []
YAML

cat > "$BASE/c/cjson/1.7.18/notes.md" << 'MD'
# cjson 1.7.18 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-26
- 编译器: clang
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cjson/RELEASENOTE.md" "$BASE/c/cjson/1.7.18/_meta.yaml" "$BASE/c/cjson/1.7.18/PROGRESS.md" "$BASE/c/cjson/1.7.18/README.md"
echo "cjson done"

### === cmake ===
cat > "$BASE/c/cmake/manifest.yaml" << 'YAML'
software: cmake
display: "CMake"
description: "跨平台构建系统生成器"
category: build-tool
homepage: "https://cmake.org/"
license: BSD-3-Clause
build_system: cmake

ohos_adaptation:
  key_points:
    - "需要设置 CMAKE_SYSTEM_NAME=OHOS"
    - "Bootstrap 阶段需 --no-qt-gui"
  common_dependencies: []

versions:
  "3.30.0":
    status: built
    build_date: "2026-04-25"
YAML

cat > "$BASE/c/cmake/README.md" << 'MD'
# CMake

CMake 是一个跨平台的构建系统生成器，用于管理构建过程。

## 功能概述

- 生成 Makefile、Ninja、Visual Studio 等多种构建系统
- 跨平台 C/C++ 项目管理
- 支持 out-of-source 构建
- 丰富的 FindXXX 模块
- CPack 打包和 CTest 测试集成

## OHOS 适配

- 构建系统为 cmake（bootstrap）
- 需要设置 CMAKE_SYSTEM_NAME=OHOS
- Bootstrap 阶段需要 --no-qt-gui

## 依赖关系

- C/C++ 编译器
- OpenSSL（可选）
- curl（可选）

## 参考资料

- 官网: https://cmake.org/
- 源码: https://github.com/Kitware/CMake
MD

cat > "$BASE/c/cmake/3.30.0/manifest.yaml" << 'YAML'
version: "3.30.0"
status: built
build_date: "2026-04-25"

source:
  url: "https://github.com/Kitware/CMake/releases/download/v3.30.0/cmake-3.30.0.tar.gz"
  tar_format: tar.gz

build:
  system: cmake
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/cmake/3.30.0/notes.md" << 'MD'
# cmake 3.30.0 适配笔记

## 编译环境
- 构建系统: cmake（bootstrap）
- 编译日期: 2026-04-25
- 编译器: clang/clang++
- 状态: compiling

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cmake/3.30.0/_meta.yaml" "$BASE/c/cmake/3.30.0/PROGRESS.md" "$BASE/c/cmake/3.30.0/README.md"
echo "cmake done"

### === cmocka ===
cat > "$BASE/c/cmocka/manifest.yaml" << 'YAML'
software: cmocka
display: "cmocka"
description: "C 语言 mock 对象测试框架"
category: foundation
homepage: "https://cmocka.org/"
license: Apache-2.0
build_system: autotools

ohos_adaptation:
  key_points:
    - "标准 autotools 项目"
  common_dependencies: []

versions:
  "2.0.2":
    status: partial
    build_date: "2026-04-27"
YAML

cat > "$BASE/c/cmocka/README.md" << 'MD'
# cmocka

cmocka 是一个优雅的 C 语言单元测试框架，支持 mock 对象。

## 功能概述

- C 语言单元测试框架
- 支持 mock 对象和函数
- 支持 setup/teardown
- 内存泄漏检测
- 多种输出格式

## OHOS 适配

- 标准 autotools 项目，无需特殊补丁

## 依赖关系

- C 编译器

## 参考资料

- 官网: https://cmocka.org/
MD

cat > "$BASE/c/cmocka/2.0.2/manifest.yaml" << 'YAML'
version: "2.0.2"
status: partial
build_date: "2026-04-27"

source:
  url: "https://cmocka.org/files/2.0/cmocka-2.0.2.tar.xz"
  tar_format: tar.xz

build:
  system: autotools
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/cmocka/2.0.2/notes.md" << 'MD'
# cmocka 2.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cmocka/RELEASENOTE.md" "$BASE/c/cmocka/2.0.2/_meta.yaml" "$BASE/c/cmocka/2.0.2/PROGRESS.md" "$BASE/c/cmocka/2.0.2/README.md"
echo "cmocka done"

### === cmph ===
cat > "$BASE/c/cmph/manifest.yaml" << 'YAML'
software: cmph
display: "C Minimal Perfect Hash"
description: "C 语言最小完美哈希函数库"
category: data
homepage: "https://cmph.sourceforge.net/"
license: LGPL-2.1
build_system: autotools

ohos_adaptation:
  key_points:
    - "标准 autotools 项目"
  common_dependencies: []

versions:
  "2.0":
    status: built
    build_date: "2026-04-24"
YAML

cat > "$BASE/c/cmph/README.md" << 'MD'
# cmph

C Minimal Perfect Hash 函数库，用于生成最小完美哈希函数。

## 功能概述

- 生成最小完美哈希函数
- 支持多种算法（CMPH、BMZ、CHD 等）
- 适用于静态集合的快速查找
- O(1) 查找时间

## OHOS 适配

- 标准编译项目

## 依赖关系

- C 编译器

## 参考资料

- 官网: https://cmph.sourceforge.net/
MD

cat > "$BASE/c/cmph/2.0/manifest.yaml" << 'YAML'
version: "2.0"
status: built
build_date: "2026-04-24"

source:
  url: "https://sourceforge.net/projects/cmph/files/cmph/cmph-2.0.tar.gz/download"
  tar_format: tar.gz

build:
  system: autotools
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/cmph/2.0/notes.md" << 'MD'
# cmph 2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: compiling

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cmph/2.0/_meta.yaml" "$BASE/c/cmph/2.0/PROGRESS.md" "$BASE/c/cmph/2.0/README.md"
echo "cmph done"

### === cunit ===
cat > "$BASE/c/cunit/manifest.yaml" << 'YAML'
software: cunit
display: "CUnit"
description: "C 语言单元测试框架"
category: foundation
homepage: "https://cunit.sourceforge.net/"
license: LGPL-2.0
build_system: custom

ohos_adaptation:
  key_points:
    - "autotools configure 在 HarmonyOS 上因临时文件权限问题失败"
    - "需要手动编译：手动生成 CUnit.h + 编译源文件 + 创建静态库"
  common_dependencies: []

versions:
  "2.1-3":
    status: success
    build_date: "2026-04-27"
YAML

cat > "$BASE/c/cunit/README.md" << 'MD'
# CUnit

CUnit 是一个 C 语言的单元测试框架，提供编写、管理和运行测试用例的系统。

## 功能概述

- C 语言单元测试框架
- 支持测试套件和测试用例的组织
- 多种输出界面（控制台、自动、Basic 等）
- 断言宏
- 注册和执行测试

## OHOS 适配

- autotools configure 在 HarmonyOS 上因临时文件权限问题失败
- 需要手动编译方式绕过：
  1. 手动替换 CUnit.h.in 中的 @VERSION@ 和 @RELEASE@
  2. 手动编译源文件
  3. 创建静态库 libcunit.a

## 依赖关系

- C 编译器

## 参考资料

- 官网: https://cunit.sourceforge.net/
MD

cat > "$BASE/c/cunit/2.1-3/manifest.yaml" << 'YAML'
version: "2.1-3"
status: success
build_date: "2026-04-27"

source:
  url: "http://downloads.sourceforge.net/project/cunit/CUnit/2.1-3/CUnit-2.1-3.tar.bz2"
  tar_format: tar.bz2

build:
  system: custom
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []

knowledge_gained:
  - "E072: config.sub/config.guess 需要更新以支持 HarmonyOS"
  - "E064: 鸿蒙系统上的 autotools 临时文件创建问题"
YAML

cat > "$BASE/c/cunit/2.1-3/notes.md" << 'MD'
# cunit 2.1-3 适配笔记

## 编译环境
- 构建系统: custom（手动编译，绕过 autotools）
- 编译日期: 2026-04-27
- 编译器: clang
- 状态: success

## 编译步骤
autotools configure 失败，采用手动编译：
1. 手动替换 CUnit.h.in 中的 @VERSION@ 和 @RELEASE@
2. 手动编译所有 C 源文件
3. 创建静态库 libcunit.a

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 创建临时文件权限错误 | HarmonyOS HMDFS 临时文件权限限制 | 手动编译绕过 autotools |
| 2 | config.sub/config.guess 不识别 HarmonyOS | 需要更新为支持 ohos 的版本 | 更新配置文件 |

## 交付物
| 文件 | 说明 |
|------|------|
| libcunit.a | 静态库 (111KB) |
| CUnit.h + 12 个头文件 | 头文件 |
| cunit-2.1-3-ohos-aarch64.tar.gz | 预编译包 |
| cunit-2.1-3-ohos-aarch64-debug.tar.gz | Debug 包 |
MD

rm -f "$BASE/c/cunit/RELEASENOTE.md" "$BASE/c/cunit/2.1-3/_meta.yaml" "$BASE/c/cunit/2.1-3/PROGRESS.md" "$BASE/c/cunit/2.1-3/README.md" "$BASE/c/cunit/install.sh"
echo "cunit done"

### === cpptoml ===
cat > "$BASE/c/cpptoml/manifest.yaml" << 'YAML'
software: cpptoml
display: "cpptoml"
description: "C++ TOML 配置文件解析器（header-only）"
category: data
homepage: "https://github.com/skystrife/cpptoml"
license: MIT
build_system: cmake

ohos_adaptation:
  key_points:
    - "Header-only 库，编译简单"
  common_dependencies: []

versions:
  "v0.1.1":
    status: partial
    build_date: "2026-04-27"
YAML

cat > "$BASE/c/cpptoml/README.md" << 'MD'
# cpptoml

cpptoml 是一个 C++ 的 TOML 配置文件解析器，header-only 库。

## 功能概述

- 解析 TOML 配置文件格式
- Header-only，无需编译，直接包含头文件
- C++11 标准

## OHOS 适配

- Header-only 库，编译和安装非常简单

## 依赖关系

- C++11 编译器

## 参考资料

- 源码: https://github.com/skystrife/cpptoml
MD

cat > "$BASE/c/cpptoml/v0.1.1/manifest.yaml" << 'YAML'
version: "v0.1.1"
status: partial
build_date: "2026-04-27"

source:
  url: "https://api.github.com/repos/skystrife/cpptoml/tarball/v0.1.1"
  tar_format: tar.gz

build:
  system: cmake
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/cpptoml/v0.1.1/notes.md" << 'MD'
# cpptoml v0.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-27
- 编译器: clang/clang++
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cpptoml/RELEASENOTE.md" "$BASE/c/cpptoml/v0.1.1/_meta.yaml" "$BASE/c/cpptoml/v0.1.1/PROGRESS.md" "$BASE/c/cpptoml/v0.1.1/README.md"
echo "cpptoml done"

### === croaring ===
cat > "$BASE/c/croaring/manifest.yaml" << 'YAML'
software: croaring
display: "CRoaring"
description: "C/C++ Roaring Bitmap 高性能位图库"
category: data
homepage: "https://roaringbitmap.org/"
license: Apache-2.0
build_system: cmake

ohos_adaptation:
  key_points:
    - "CMake 构建，需禁用测试"
  common_dependencies: []

versions:
  "4.6.1":
    status: success
    build_date: "2026-04-24"
YAML

cat > "$BASE/c/croaring/README.md" << 'MD'
# CRoaring

CRoaring 是 Roaring Bitmap 的 C/C++ 实现，提供高性能的压缩位图操作。

## 功能概述

- 高性能压缩位图（Roaring Bitmap）
- 支持位集合的并集、交集、差集等操作
- 支持序列化和反序列化
- C 和 C++ API

## OHOS 适配

- CMake 构建，使用 `-DENABLE_ROARING_TESTS=OFF` 禁用测试
- 编译成功，状态为 success

## 依赖关系

- C/C++ 编译器

## 参考资料

- 官网: https://roaringbitmap.org/
- 源码: https://github.com/RoaringBitmap/CRoaring
MD

cat > "$BASE/c/croaring/4.6.1/manifest.yaml" << 'YAML'
version: "4.6.1"
status: success
build_date: "2026-04-24"

source:
  url: "https://github.com/RoaringBitmap/CRoaring/archive/refs/tags/v4.6.1.tar.gz"
  tar_format: tar.gz

build:
  system: cmake
  configure_options:
    - "-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX"
    - "-DCMAKE_BUILD_TYPE=Release"
    - "-DENABLE_ROARING_TESTS=OFF"
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/croaring/4.6.1/notes.md" << 'MD'
# croaring 4.6.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-04-24
- 编译器: clang/clang++
- 状态: success

## 编译步骤
使用 CMake 标准构建流程，禁用测试模块。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/croaring/RELEASENOTE.md" "$BASE/c/croaring/4.6.1/_meta.yaml" "$BASE/c/croaring/4.6.1/PROGRESS.md" "$BASE/c/croaring/4.6.1/README.md"
echo "croaring done"

### === cryptopp ===
cat > "$BASE/c/cryptopp/manifest.yaml" << 'YAML'
software: cryptopp
display: "Crypto++"
description: "C++ 加密算法库"
category: crypto
homepage: "https://www.cryptopp.com/"
license: BSL-1.0
build_system: makefile

ohos_adaptation:
  key_points:
    - "大型加密库，需要较长编译时间"
  common_dependencies: []

versions:
  "8.9.0":
    status: partial
    build_date: "2026-04-24"
YAML

cat > "$BASE/c/cryptopp/README.md" << 'MD'
# Crypto++

Crypto++ 是一个免费的 C++ 加密算法库，包含大量加密方案的实现。

## 功能概述

- 对称加密：AES、DES、Blowfish 等
- 非对称加密：RSA、DSA、ECDSA 等
- 哈希函数：SHA、MD5、BLAKE2 等
- 消息认证码：HMAC、CMAC 等
- 数字签名和证书

## OHOS 适配

- 大型加密库（107.6MB 包大小）
- 编译进行中

## 依赖关系

- C++ 编译器

## 参考资料

- 官网: https://www.cryptopp.com/
- 源码: https://github.com/weidai11/cryptopp
MD

cat > "$BASE/c/cryptopp/8.9.0/manifest.yaml" << 'YAML'
version: "8.9.0"
status: partial
build_date: "2026-04-24"

source:
  url: "https://api.github.com/repos/weidai11/cryptopp/tarball/CRYPTOPP_8_9_0"
  tar_format: tar.gz

build:
  system: makefile
  configure_options: []
  dependencies: []
  cc: clang
  cxx: clang++

patches_applied: []
knowledge_gained: []
YAML

cat > "$BASE/c/cryptopp/8.9.0/notes.md" << 'MD'
# cryptopp 8.9.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-24
- 编译器: clang/clang++
- 状态: partial

## 编译步骤
编译进行中。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| — | 无重大问题 | — | — |
MD

rm -f "$BASE/c/cryptopp/RELEASENOTE.md" "$BASE/c/cryptopp/8.9.0/_meta.yaml" "$BASE/c/cryptopp/8.9.0/PROGRESS.md" "$BASE/c/cryptopp/8.9.0/README.md"
echo "cryptopp done"

echo "=== Batch 1 (c-ares through cryptopp) complete ==="
