# airspyone-host 1.0.10 — 适配笔记

## 基本信息
- **软件**: airspyone-host (AirSpy user-mode driver and associated tools)
- **版本**: 1.0.10
- **来源**: https://github.com/airspy/airspyone_host (tag v1.0.10)
- **构建系统**: CMake (非 autotools)
- **许可**: GPL/BSD (混合)

## 依赖
- **libusb-1.0**: 使用预编译包 libusb 1.0.27 (cmd-pkgs)
- **pthread**: 系统内置
- **libxml2**: 已安装 (lld 链接器间接依赖)

## 编译参数
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

**注意**:
- 不需要 `./configure`（CMake 项目）
- `cmake_minimum_required(VERSION 2.8)` 需要加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x
- 必须设置 `PKG_CONFIG_PATH` 包含 libusb 的 pkgconfig 路径
- **不要**设置 `LD_LIBRARY_PATH` 包含 `~/usr/local/lib`（会导致 lld 链接器找不到 libxml2.so.16，系统默认路径已正确）

## 源码修改

### 修改1: libairspy/src/CMakeLists.txt — 安装目标条件
**原因**: CMake 在 HarmonyOS 上不设置 `UNIX` 变量（系统未被识别），导致库和头文件的 install 目标被跳过。
**修改**: `if(${UNIX})` → `if(NOT WIN32)`
**影响**: 库 (libairspy.so, libairspy.a) 和头文件现在可以正确安装

## 平台陷阱
1. **CMAKE_SYSTEM_NAME 未识别**: CMake 输出 "System is unknown to cmake"，但不影响编译
2. **lld 依赖 libxml2.so.16**: 链接器 lld 需要 libxml2，系统默认能找到，但显式设置 LD_LIBRARY_PATH 反而会干扰
3. **RPATH 问题**: 安装的二进制文件使用相对 RPATH (`../../libairspy/src/`)，在 staging 目录中无法直接运行，需从 build 目录运行

## 测试
- 无 `make check` 目标（CMake 项目无 CTest 定义）
- Smoke test: `airspy_lib_version` 输出 "AirSpy lib version: 1.0.10" ✅
- `airspy_info` 输出版本并报告无 USB 设备（预期行为）✅
---

**编译结束**: 2026-06-29 17:25
**最终状态**: built
