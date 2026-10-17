# libusb-compat 0.1.7 适配笔记

## 编译环境
- 构建系统: cmake (custom CMakeLists.txt via patch — upstream is autotools-only)
- 编译日期: 2026-08-24
- 编译器: clang/clang++
- 状态: built (前置适配完成，待真机验证)

## 编译步骤

上游 libusb-compat 0.1.7 仅提供 autotools 构建系统。由于 HarmonyOS HMDFS 文件系统的
hmmac 强制访问控制限制，autotools 的临时文件操作会被阻断。因此通过补丁添加了自定义
CMakeLists.txt。

1. `conan create . --build=missing` 使用 CMake 构建
2. CMakeLists.txt 通过 `find_package(libusb-1.0 CONFIG REQUIRED)` 查找 Conan 注入的依赖
3. 构建产物为 `libusb.so`（共享库）或 `libusb.a`（静态库）
4. 安装 `usb.h` 头文件和 `libusb.pc` pkg-config 文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools configure 失败 | HMDFS hmmac 阻断 mktemp 等临时文件操作 | 添加 CMakeLists.txt 补丁，用 CMake 替代 |
| 2 | 上游无 CMakeLists.txt | libusb-compat 上游仅支持 autotools | 从零编写 CMakeLists.txt 补丁 |
| 3 | Conan 依赖注入 | pkg_check_modules 在交叉编译时不可靠 | 改用 find_package(libusb-1.0 CONFIG) + Conan CMakeDeps |

## 源码修改

- `0001-CMakeLists.txt.patch`：添加完整的 CMakeLists.txt（使用 Conan 兼容的 find_package）
- `0002-config.h.cmake.patch`：添加 config.h.cmake 模板
- `0003-libusb.pc.in.patch`：修复 libusb.pc.in 的 Version 字段

## 依赖版本

- libusb/1.0.27 (Conan 包，已发布到制品仓)

## 验证结果

```bash
# 待真机验证：
CI_PACKAGES="archives/l/libusb-compat/0.1.7" zsh ci/conan/build_and_test.sh
```

## 注意事项

- 库安装名为 `libusb`（不是 `libusb-compat`），符合上游惯例
- pkg-config 包名为 `libusb`（兼容旧的 libusb-0.1 pc 名称）
- 上游无测试套件（整个库只有一个 core.c 源文件）
- test_package 验证 usb_init / usb_find_busses / usb_strerror 等核心 API

---

**编译结束**: 2026-08-24
**最终状态**: 前置适配完成，待真机/shadow CI 验证
