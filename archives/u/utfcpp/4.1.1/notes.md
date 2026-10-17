# utfcpp 4.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: built（HarmonyOS 验证通过）
- 特殊说明: header-only 库，无需编译二进制

## 库简介

utfcpp 是一个用于 C++ 的 UTF-8 处理库，提供便携式 UTF-8 编码/解码、
迭代、校验等功能。
- 上游仓库: https://github.com/nemtrif/utfcpp
- 许可证: BSL-1.0
- 类型: header-only（INTERFACE library，CMake target utf8cpp::utf8cpp）

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方，使用 CMake 工具链
- `conandata.yml`: 源码下载 URL 和 SHA256
- `test_package/`: 消费者测试，验证 utfcpp 头文件可用性

### 关键配置
- `package_type = "header-library"`：声明为纯头文件库
- `package_id` 使用 `self.info.clear()`：所有 settings 组合产出相同包
- `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=str(self.settings.arch)`：规避 E092（CMake 不识别 OHOS）
- `UTF8CPP_ENABLE_TESTS=ON`：构建并执行完整上游 CTest 测试
- `UTF8CPP_ENABLE_BENCHMARKS=OFF`：关闭 benchmark（需要额外依赖）

### 平台适配
- R32: `self.settings.os in ("Linux", "OHOS")` 平台判断
- E092: 通过 CMakeToolchain 设置 CMAKE_SYSTEM_NAME=Linux 规避鸿蒙平台未知问题

## 依赖

utfcpp 是 header-only 库，无外部依赖。

## 测试说明

### 上游测试（实测，rule 4）
上游使用自定义 ftest 框架 + CMake/CTest，`tests/` 目录下 6 个测试可执行文件：
- negative: 12 个用例（无效 UTF-8 输入拒绝）
- cpp11: 10 个用例（C++11 API）
- cpp17: 9 个用例（C++17 API）
- cpp20: 8 个用例（C++20 API）
- apitests: 33 个用例（checked/unchecked API + iterator）
- noexceptionstests: 15 个用例（-fno-exceptions 编译）

**实测通过率 87/87 = 100%**（本地 ctest 全绿：6 个 ctest 全部 Passed）。

### test_package 测试
- 文件: `test_package/CMakeLists.txt` + `test_package/test.cpp`
- 验证内容:
  1. `#include <utf8.h>` 头文件可被包含
  2. `utf8::utf8to32` / `utf8::utf8to16` 基础 API 调用
  3. 头文件安装位置正确（include/utf8cpp）

## 验证结果

HarmonyOS 冷构建通过：上游 CTest 87/87（100%），Conan `test_package` 消费者测试 1/1。

## 注意事项

1. **Header-only 库特性**：utfcpp 无需编译二进制，只需 CMake 配置和头文件安装
2. **CMake 目标**：安装后可通过 `find_package(utf8cpp)` 和 `utf8cpp::utf8cpp` 目标链接
3. **C++ 标准**：支持 C++11/14/17/20（上游测试分别验证）
4. **无 ELF 签名**：header-only 库无二进制文件，不需要 ELF 签名和 RPATH 设置
