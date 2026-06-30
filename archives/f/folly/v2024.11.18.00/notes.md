# folly v2024.11.18.00 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: **built**（核心库编译成功）

## 编译步骤

1. **源码下载**：使用 Gitee 镜像下载（GitHub 超时）
   - URL: https://gitee.com/mirrors/folly/repository/archive/v2024.11.18.00.tar.gz

2. **CMake 配置尝试**：
   ```bash
   cd ~/tmp/builds/folly-v2024.11.18.00.work
   mkdir -p build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   ```

3. **遇到问题并修复**：
   - 修改 CMakeLists.txt 第 15 行：`cmake_minimum_required(VERSION 3.5)`（原 VERSION 3.0.2 不兼容）
   - 注释掉 CMakeLists.txt 第 73-74 行的 Facebook 内部构建代码（FBBuildOptions 缺失）

4. **最终失败**：CMake 配置失败，缺少必需依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 Gitee 镜像 | ✅ 已解决 |
| 2 | CMake 版本不兼容 | cmake_minimum_required(VERSION 3.0.2) 不被 CMake 4.1.2 支持 | 修改为 VERSION 3.5 | ✅ 已解决 |
| 3 | FBBuildOptions 缺失 | 开源版本缺少 fbcode_builder 构建工具 | 注释相关代码 | ✅ 已解决 |
| 4 | 缺少依赖包 | cmd-pkgs 无预编译包 | 需要手动编译依赖 | ❌ 未解决 |

## 依赖版本

### 已安装的预编译包
- ✅ gflags 2.2.2
- ✅ openssl 1.1.1w
- ✅ zlib 1.3.1

### 正在安装（耗时过长）
- ⏳ boost 1.84.0（下载完成，安装超时）

### 缺少预编译包（需手动编译）
- ❌ double-conversion（必需）
- ❌ fmt（必需）
- ❌ libevent 2.1.12（必需）
- ❌ glog 0.7.1（可选但常见）
- ❌ lz4 1.10.0（可选）
- ❌ snappy 1.2.2（可选）

## 验证结果

```bash
# CMake 配置失败
CMake Error at CMakeLists.txt:XX (find_package):
  Could not find a package configuration file provided by "double-conversion"
  with any of the following names:
    double-conversionConfig.cmake
    double-conversion-config.cmake
```

## 失败原因总结

### 核心问题
1. **依赖链过长**：folly 需要多个依赖库，其中 double-conversion、fmt、libevent 在 cmd-pkgs 中无预编译包
2. **构建系统不完整**：从 Gitee 下载的开源版本缺少 Facebook 内部构建工具（fbcode_builder）
3. **网络限制**：无法直接访问 GitHub，依赖镜像站点

### 可行方案

**方案 A: 先编译依赖**（推荐）
1. 创建子任务编译 double-conversion、fmt、libevent
2. 将这些依赖添加到 cmd-pkgs 预编译包
3. 重新编译 folly

**方案 B: 使用替代库**
- folly 主要用于 Facebook 内部项目
- 部分功能可用其他库替代：
  - fmt 可替代 folly 的格式化功能
  - boost 可提供部分并发和容器功能

**方案 C: 暂缓编译**
- 等待 cmd-pkgs 补充 folly 所需依赖的预编译包
- 等待构建系统适配方案完善

## 交付物

无（编译失败，无打包产物）

## 注意事项

⚠️ **不要删除此归档**：虽然编译失败，但记录了重要的诊断信息和已解决的问题，对后续编译有参考价值。

📋 **后续步骤建议**：
1. 按依赖顺序编译：double-conversion → fmt → libevent → folly
2. 考虑使用 folly 的精简版本或替代方案
3. 补充 cmd-pkgs 预编译包库

## 源码修改记录

1. **CMakeLists.txt 第 15 行**：
   ```cmake
   # 原：cmake_minimum_required(VERSION 3.0.2)
   # 改：cmake_minimum_required(VERSION 3.5)
   ```

2. **CMakeLists.txt 第 73-74 行**：
   ```cmake
   # 注释掉 FBBuildOptions 相关代码
   # include(FBBuildOptions)
   # fb_activate_static_library_option()
   ```

## 编译时长统计

- 源码下载：约 10 分钟（含网络问题尝试）
- 依赖安装：约 7+ 分钟（Boost 仍在安装）
- 总耗时：超过 20 分钟，尚未进入实际编译阶段

---

## 第二次编译尝试（2026-05-26）

### 问题发现
- **Boost 只安装了头文件**：缺少编译好的库文件
- folly 需要 Boost 的编译版本（context, filesystem, program_options, regex, system, thread）
- FastFloat 已安装 ✅
- abseil-cpp 已安装 ✅

### 必需依赖状态
| 依赖 | 状态 | 备注 |
|------|------|------|
| double-conversion 3.3.0 | ✅ | 静态库已安装 |
| fmt 10.2.1 | ✅ | 静态库已安装 |
| libevent 2.1.12 | ✅ | 共享库已安装 |
| boost 1.84.0 | ⚠️ | **只有头文件，缺少编译库** |
| openssl 1.1.1w | ✅ | 已安装 |
| gflags 2.2.2 | ✅ | 静态库已安装 |
| abseil-cpp 20260107.1 | ✅ | 已安装 |
| FastFloat | ✅ | header-only 已安装 |

### 解决方案
需要编译 Boost 的完整版本（包含 context, filesystem, program_options, regex, system, thread 组件）

---

## 第三次编译尝试（2026-05-26） - 成功！

### 最终解决方案
由于 Boost 编译库下载困难，采用以下方案：
1. **修改 folly-deps.cmake**：将 Boost 改为 header-only 模式
2. **创建缺失的 Find 模块**：
   - FindDoubleConversion.cmake
   - FindLibEvent.cmake
   - FindGlog.cmake
3. **添加 OpenHarmony 平台识别**：
   - 添加 `__OHOS__` 编译定义
   - 修复 `FOLLY_ELF_NATIVE_CLASS` 定义（使用 __aarch64__ 检测）
4. **修复 glog 兼容性**：
   - 添加 `GLOG_USE_GLOG_EXPORT` 编译定义到所有 target
   - folly_base, folly_test_util, follybenchmark, logging_example_lib 等
5. **修复 Boost pthread cancellation**：
   - 修改 `boost/core/detail/sp_thread_sleep.hpp`，添加 `__OHOS__` 条件跳过 pthread_setcancelstate

### 源码修改汇总

#### CMakeLists.txt
- 第 459-464 行：添加 `GLOG_USE_GLOG_EXPORT` 和 `__OHOS__` 到 folly_base
- 第 483-497 行：添加 `target_compile_definitions` 到 folly_test_util
- 第 634-640 行：添加编译定义到 folly_test_support

#### folly/CMakeLists.txt
- 第 21-29 行：添加编译定义到 follybenchmark

#### folly/logging/example/CMakeLists.txt
- 第 6-11 行：添加编译定义到 logging_example_lib 和 logging_example

#### folly/debugging/symbolizer/Elf.cpp
- 第 38-49 行：修复 `FOLLY_ELF_NATIVE_CLASS` 定义（添加 `__OHOS__` 条件）

#### CMake/folly-deps.cmake
- 第 39-43 行：将 Boost 改为 header-only 模式（移除 REQUIRED 组件）

#### 新创建的 Find 模块
- CMake/FindDoubleConversion.cmake
- CMake/FindLibEvent.cmake
- CMake/FindGlog.cmake

#### Boost 头文件修改（系统级）
- `/storage/Users/currentUser/usr/local/include/boost/core/detail/sp_thread_sleep.hpp`
  - 第 59-61 行：添加 `__OHOS__` 条件
  - 第 88-90 行：添加 `__OHOS__` 条件

### 编译结果

**成功编译的产物**：
- libfolly.a（126MB）
- libfolly_test_util.a（2MB）
- libfollybenchmark.a（3.8MB）
- libfolly.pc（pkg-config 文件）
- 122 个头文件

**编译状态**：`built`（核心库编译成功）

**注意事项**：
- logging_example 链接失败（需要额外设置库路径），不影响核心库
- Boost 使用 header-only 模式，部分功能可能受限
- folly 主要作为基础库，需要其他库依赖时才能完整使用

### 遇到的平台问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| glog GLOG_EXPORT 未定义 | glog 0.7+ 需要 GLOG_USE_GLOG_EXPORT 宏 | 添加到所有 target 的编译定义 |
| pthread_setcancelstate 未实现 | 鸿蒙系统 syscall 限制（E051） | 修改 Boost 源码跳过 pthread cancellation |
| FOLLY_ELF_NATIVE_CLASS 未定义 | 平台识别缺失 | 使用 __aarch64__ 检测直接定义 64 |
| Find 模块缺失 | folly 使用 MODULE 模式查找依赖 | 创建自定义 Find 模块 |

### 编译时长

- CMake 配置：约 2 分钟
- 编译 folly_base：约 10 分钟
- 总耗时：约 15 分钟

---

## 第二次编译尝试（2026-05-26）

### 问题发现
- **Boost 只安装了头文件**：缺少编译好的库文件
- folly 需要 Boost 的编译版本（context, filesystem, program_options, regex, system, thread）
- FastFloat 已安装 ✅
- abseil-cpp 已安装 ✅

### 必需依赖状态
| 依赖 | 状态 | 备注 |
|------|------|------|
| double-conversion 3.3.0 | ✅ | 静态库已安装 |
| fmt 10.2.1 | ✅ | 静态库已安装 |
| libevent 2.1.12 | ✅ | 共享库已安装 |
| boost 1.84.0 | ⚠️ | **只有头文件，缺少编译库** |
| openssl 1.1.1w | ✅ | 已安装 |
| gflags 2.2.2 | ✅ | 静态库已安装 |
| abseil-cpp 20260107.1 | ✅ | 已安装 |
| FastFloat | ✅ | header-only 已安装 |

### 解决方案
需要编译 Boost 的完整版本（包含 context, filesystem, program_options, regex, system, thread 组件）
---

**编译结束**: 2026-05-26 11:08
**最终状态**: built
