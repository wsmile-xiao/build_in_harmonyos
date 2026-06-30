# cryptominisat 5.14.4 编译记录

## 基本信息
- 软件: cryptominisat
- 版本: 5.14.4
- 构建系统: CMake
- 编译日期: 2026-05-20

## 编译过程

### 1. 初始化
- 源码已下载并解压到 `cryptominisat-5.14.4.work`
- 构建系统识别为 CMake

### 2. 配置阶段
- **问题**: CMake 不识别 HarmonyOS 平台，导致编译器检测失败
- **解决**: 设置 `CMAKE_SYSTEM_NAME=Linux` 覆盖平台检测

### 3. 编译阶段
- **问题**: HarmonyOS libcxx (clang 15) 不完整支持 C++20 ranges
  - `std::views::iota` 不支持
  - `std::ranges::find` 不支持
- **解决**: 创建条件编译补丁，使用 `#ifdef __OHOS__` 提供替代实现

### 4. 打包阶段
- 预编译包已生成:
  - `cryptominisat-5.14.4-ohos-aarch64.tar.gz` (57MB)
  - `cryptominisat-5.14.4-ohos-aarch64-debug.tar.gz` (29MB)

## 补丁说明

### 0001-ohos-fix-cpp20-ranges-compatibility.patch
修改 `src/constants.h`，条件编译处理 `#include <ranges>` 和 `std::views::iota`

### 0002-ohos-fix-std-ranges-find.patch
修改 `src/alg.h`，用 `std::find` 替代 `std::ranges::find`

### 0003-ohos-fix-iota-loop.patch
修改 `src/solver.cpp`，用传统 for 循环替代 `std::views::iota` 范围遍历

## 编译产物
- `cryptominisat5` 可执行文件
- `libcryptominisat5.a` 静态库
- `libcadical.a`, `libcadiback.a` 依赖库

## 知识提取
- HarmonyOS libcxx 对 C++20 支持有限，需要条件编译兼容
- CMake 平台检测可通过 CMAKE_SYSTEM_NAME 覆盖