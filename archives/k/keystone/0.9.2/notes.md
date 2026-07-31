# keystone 0.9.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-30
- 编译器: clang 15.0.4 / clang++
- Conan 版本: 2.29.1
- Python 版本: 3.12.9
- 状态: built

## 软件简介

Keystone 是一个轻量级、多平台、多架构的汇编器框架，基于 LLVM 实现。支持
ARM、ARM64 (AArch64)、EVM、Hexagon、Mips、PowerPC、Sparc、SystemZ 和 X86
（16/32/64 位）架构。提供 C/C++ API，线程安全，双许可证（GPLv2 + 商业）。

## Conan 配方构建

通过 `conan create` 驱动 CMake 构建，配方为 `conanfile.py`。

### 构建配置

```python
# conanfile.py generate() 关键配置
tc.variables["BUILD_SHARED_LIBS"] = "OFF"        # 默认静态库
tc.variables["BUILD_LIBS_ONLY"] = False          # 构建 kstool 可执行文件
tc.variables["LLVM_TARGETS_TO_BUILD"] = "all"    # 支持全部架构
tc.extra_cxxflags.append("-fcommon")             # 合并 common symbols
tc.extra_cflags.append("-fcommon")
# CMAKE_POLICY_VERSION_MINIMUM 通过 cmake.configure(variables=...) 以 -D 命令行
# cache 变量传递，不能放入 tc.variables（toolchain 文件加载晚于 cmake_minimum_required）
cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
```

### 依赖关系

无外部 Conan 依赖。LLVM 作为 vendored 源码内嵌在 `llvm/` 目录，由
`add_subdirectory(llvm)` 直接构建，不需要系统 LLVM。

### 构建命令

```bash
# 构建 keystone
conan create archives/k/keystone/0.9.2/ --build=missing \
  -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64

# CI 验证
CI_PACKAGES="archives/k/keystone/0.9.2" zsh ci/conan/build_and_test.sh
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接时重复符号错误 | 旧版 vendored LLVM 含 common symbols（临时定义），clang 15+ 默认 -fno-common 导致重复符号 | generate() 中添加 `-fcommon` 到 cxxflags/cflags |
| 2 | CMake 策略兼容性 | cmake_minimum_required(VERSION 2.8.7) 与新版 CMake 不兼容 | 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | CI #11099 构建失败：`Compatibility with CMake < 3.5 has been removed` | `tc.variables["CMAKE_POLICY_VERSION_MINIMUM"]` 写入 conan_toolchain.cmake 作为普通 set()，而 toolchain 文件在 project() 时才加载，晚于源码 CMakeLists.txt:4 的 cmake_minimum_required()，导致 CMake 3.27+ 解析 cmake_minimum_required 时读不到该变量 | 改用 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 以 -D 命令行 cache 变量传递，在 cmake_minimum_required() 解析前就被 CMake 读到 |
| 4 | CI #11153 构建失败：`config.guess: unable to guess system type` | vendored LLVM 使用 2011 年版 `config.guess`，没有 HarmonyOS 分支；未知系统会进入需要可写临时目录的编译探测，在 CI 中先触发 Permission denied，即使目录可写也无法识别 HarmonyOS | 给 `llvm/cmake/config.guess` 增加 aarch64 HarmonyOS 分支，返回旧 LLVM 可接受的 `aarch64-unknown-linux-ohos` |
| 5 | CI #11153 配置阶段同时报错：`Policy CMP0051 may not be set to OLD behavior` | 顶层和 vendored LLVM 的 CMake 文件均显式要求 CMP0051 OLD；新版 CMake 已删除该兼容行为 | 将两处 CMP0051 显式切换为新版 CMake 要求的 NEW 行为 |
| 6 | CI #11288 配置失败：`HandleLLVMOptions.cmake:125 Unable to determine platform` | CI 的 CMake 将目标系统识别为 `HarmonyOS`，但没有 `Platform/HarmonyOS-Initialize.cmake`，因此内建 `UNIX` 变量为 false；旧 LLVM 随后拒绝未知平台 | 在顶层 `project()` 前注册源码内的 CMake 模块目录，增加 HarmonyOS 初始化模块设置 `UNIX=1`，并通过 `Platform/HarmonyOS.cmake` 继承 Linux 的 ELF 和链接规则 |

## 源码修改

应用 `patches/0001-config-guess-harmonyos.patch` 修复 vendored LLVM 的 HarmonyOS 主机识别，用 `patches/0002-cmake-cmp0051-new.patch` 适配新版 CMake 已移除的 CMP0051 OLD 行为，并用 `patches/0003-cmake-harmonyos-platform.patch` 补齐 CMake 的 HarmonyOS Unix 平台初始化和 Linux 兼容链接规则；其余兼容性问题通过 CMake 工具链变量和编译器标志解决。

## 本地 CI 模拟结果（2026-07-30）

本次验证使用 OHOS SDK 在 Windows 主机执行 aarch64 交叉构建。由于
`hdc list targets` 返回 `[Empty]`，没有在 OHOS 目标设备上执行测试程序，
因此以下结果不等同于真机原生 W3，最终以远端 CI 为准。

| 检查 | 结果 | 详情 |
|------|------|------|
| 源码校验 | PASS | 官方源码 SHA256 为 `c9b3a343ed3e05ee168d29daf89820aff9effb2c74c6803c2d9e21d55b5b7c24` |
| 补丁应用 | PASS | `0001`、`0002`、`0003` 按 `conandata.yml` 顺序干净应用 |
| CMake 配置 | PASS | 目标三元组为 `aarch64-unknown-linux-ohos`，架构为 AArch64，未再出现 `Unable to determine platform` |
| 交叉构建 | PASS | Ninja 完成 `227/227`，生成 `libkeystone.a` 与 `kstool` |
| 产物架构 | PASS | `libkeystone.a` 与 `kstool` 均确认包含 AArch64 目标代码 |
| test_package | PARTIAL | `test.cpp` 已针对 `libkeystone.a` 编译并链接，因无 OHOS 设备未执行 |
| 真机原生 W3 | NOT RUN | `hdc list targets` 返回 `[Empty]`，由远端 CI 完成最终验证 |

## 交付物

| 文件 | 说明 |
|------|------|
| libkeystone.a | 静态库（汇编引擎核心，含全部架构支持） |
| kstool | 可执行文件（命令行汇编工具） |
| keystone.pc | pkg-config 文件 |
| keystone/*.h | 头文件（keystone.h + 各架构头文件） |

## 注意事项

1. **构建系统**: 使用 cmake 构建，源码自带 CMakeLists.txt，内置 vendored LLVM
2. **混合类型**: 既有库（libkeystone）又有可执行文件（kstool），需 commands.json (R38)
3. **编译器标志**: 必须添加 -fcommon，否则旧 LLVM common symbols 链接失败
4. **无外部依赖**: LLVM 内嵌，不需要系统 LLVM 或其他 Conan 依赖
5. **构建时间**: vendored LLVM 编译较重，CI 可能需要较长时间
6. **架构支持**: LLVM_TARGETS_TO_BUILD=all 支持全部架构，可按需缩减

---

**编译结束**: 2026-07-30
**最终状态**: built
**Conan 引用**: `keystone/0.9.2`
