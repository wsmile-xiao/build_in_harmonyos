# libucl 0.9.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

### 1. init-build（自动）
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libucl 0.9.4 \
  --url=https://github.com/vstakhov/libucl/archive/refs/tags/0.9.4.tar.gz
```
自动完成源码下载、解压、骨架创建、依赖解析、环境检查。

### 2. CMake 配置
```bash
source .build-context-libucl-0.9.4
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
```
CMake 不识别 HarmonyOS 平台（输出 "System is unknown to cmake"），但不影响构建，因为底层编译器为 clang，CMake 能正确检测编译器特性。

### 3. 编译
```bash
make -j1
```
编译 9 个源文件生成 libucl.a 静态库 + 5 个测试程序。有 10 个 [-Wunused-value] 警告（src/mum.h:129），无害。

### 4. 安装
```bash
make install DESTDIR=$TEST_PREFIX
```
安装产物：libucl.a、ucl.h、ucl++.h、ucl-config.cmake、ucl-config-noconfig.cmake

### 5. 测试
```bash
ctest --output-on-failure
```
4/5 通过。test_schema 因 /tmp 只读失败（E002 平台陷阱）。

### 6. Conan 配方生成与验证
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init libucl 0.9.4
# 手动修复 conanfile.py（autotools→cmake）和 conandata.yml（sha256）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libucl 0.9.4
```
8 道门禁全部通过，conan create + test_package 测试通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成的 conanfile.py 使用 Autotools 模板 | ohc-run.py registry 记录构建系统为 "autotools"，但实际源码用 CMake | 手动重写 conanfile.py，改用 CMakeToolchain/CMake |
| 2 | conandata.yml 的 sha256 为占位符 "REPLACE_WITH_ACTUAL_SHA256" | conan-init 自动生成时未填充真实值 | 用 sha256sum 计算得到 319d8ff... 并替换 |
| 3 | conanfile.py license 标记为 "MIT" | 模板默认值 | 改为 "BSD-2-Clause"（依据 COPYING 文件） |
| 4 | package_info.libs 写为 ["libucl"] | 模板按软件名生成，但 CMake target 名为 "ucl" | 改为 ["ucl"] |
| 5 | test_package/test.c 不调用任何库函数 | 模板只打印消息 | 重写为调用 ucl_parser_new/add_string/get_object 的真实烟雾测试 |
| 6 | test_schema 测试失败 | 测试脚本 schema.test 硬编码 /tmp 路径，鸿蒙 /tmp 只读（E002） | 非代码缺陷，记录为平台限制 |
| 7 | finish 首次降级为 built | 缺少 test-report.md 和 .staging-verified | 补齐文件后重新 finish 为 published |

## 源码修改

无补丁、无源码修改。所有编译通过原始源码完成。

## 依赖版本

无外部依赖。libucl 0.9.4 自包含所有所需代码（内嵌 uthash、klib 等）。
编译环境中检测到 OpenSSL 1.1.1w（可选，用于 ENABLE_URL_SIGN 功能，默认 OFF，未使用）。

## 验证结果

```bash
# ctest 结果
80% tests passed, 1 tests failed out of 5
Total Test time (real) = 41.68 sec

# conan create test_package 结果
100% tests passed, 0 tests failed out of 1
Total Test time (real) = 0.03 sec

# 产物验证
libucl.a: ar archive (9 个目标文件)
仅依赖 libc.so（系统库）
PIE + BIND_NOW 安全特性已启用
```

## 注意事项

1. **构建系统识别**: 源码包含 configure.ac/Makefile.am（autotools）和 CMakeLists.txt（cmake）和 Makefile.unix（plain makefile），实际使用 CMake 构建。conan-init 自动生成的模板默认按 autotools 处理，需手动修正为 CMake。
2. **CMake 平台警告**: CMake 输出 "System is unknown to cmake, create: Platform/HarmonyOS"，这是已知问题（E092），不影响构建。
3. **test_schema /tmp 陷阱**: 测试脚本硬编码 /tmp 路径，鸿蒙系统 /tmp 只读。若需修复，可将 /tmp 替换为 $TMPDIR。
4. **库名称**: CMake target 名为 "ucl"（非 "libucl"），package_info.libs 必须写 ["ucl"]。
---

**编译结束**: 2026-06-29 15:30
**最终状态**: published
