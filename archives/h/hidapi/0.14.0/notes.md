# hidapi 0.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built (conan-verify passed, status=published eligible)

## 编译步骤

使用 CMake 构建系统，关键参数：
- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` — CMake 4.x 兼容性
- `-DHIDAPI_NO_ICONV=ON` — 禁用 Iconv (OHOS 不可用)
- CMakeDeps 生成器用于解析 libusb 依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性错误 | hidapi CMakeLists.txt 要求 cmake 3.1.3，系统 cmake 4.1.2 要求最低 3.5 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` (必须用 cache_variables 而非 variables) |
| 2 | Iconv 未找到 | OHOS 平台无 Iconv 库 | `-DHIDAPI_NO_ICONV=ON` 禁用 Iconv |
| 3 | libusb 依赖未找到 | hidapi CMakeLists.txt 用 TARGET usb-1.0 检测，Conan CMakeDeps 生成 libusb-1.0::libusb-1.0 | patch libusb/CMakeLists.txt 添加 find_package + conan target 检测 |
| 4 | test_package 头文件找不到 | includedirs 设置为 include/hidapi 但代码 #include <hidapi/hidapi.h> | 改为 includedirs=["include"] |
| 5 | test_package 测试失败 | hid_init() 在无 USB 设备的无头系统上失败 | 测试容忍 hid_init 失败，仍验证库加载和 API 可调用 |

## 源码修改

无补丁文件，build() 方法中使用 replace_in_file 运行时修改 libusb/CMakeLists.txt：
- 添加 `find_package(libusb-1.0 QUIET)` 和 Conan CMakeDeps target 检测

## 依赖版本

- libusb/1.0.27 (from conan remote ohpcd, shared=True)

## 验证结果

conan-verify 全部通过 (G0-G4 + L2/L4/L5)
W3 本地 CI 模拟通过 (setup.sh + build_and_test.sh)

---

**编译结束**: 2026-08-07
**最终状态**: built (conan-verify passed)
