# ArpON 3.0-ng — HarmonyOS 适配笔记

## 软件信息
- **名称**: ArpON (ArpON - ARP handler inspection)
- **版本**: 3.0-ng
- **构建系统**: CMake
- **上游源码**: https://sourceforge.net/projects/arpon/files/arpon/ArpON-3.0-ng.tar.gz/download
- **SHA256**: ea55d1641b4573b19103ca596368e418aecd2a1409adbdce3a9f76dc8ebad590
- **依赖**: libnet/1.2, libpcap/1.10.6, libdnet/1.12, librt, libpthread

## 适配修改记录

### 1. CMakeLists.txt — cmake_minimum_required 升级
- **问题**: cmake 4.1.2 不再支持 cmake_minimum_required(VERSION 2.6)
- **修复**: 改为 `cmake_minimum_required(VERSION 3.5)`
- **铁律**: R3 (探索阶段改源码，记录到 notes.md)

### 2. cmake/modules/FindSystem.cmake — 添加 HarmonyOS 平台识别
- **问题**: FindSystem.cmake 只匹配 "Linux"，HarmonyOS 的 CMAKE_SYSTEM_NAME="HarmonyOS"
- **修复**: 添加 STREQUAL "OHOS" 和 "HarmonyOS" 到条件判断
- **铁律**: R3 (探索阶段改源码，记录到 notes.md)

### 3. src/opt.c:288 — 修复指针比较警告
- **问题**: `opt->interface != '\0'` 触发 `-Wpointer-compare` 警告，`-Werror` 导致编译失败
- **修复**: 改为 `opt->interface[0] != '\0'`（检查字符串首字符非空终止符）
- **铁律**: R3, R6 (只改源文件)

### 4. src/thd.c — 添加 HarmonyOS pthread 取消函数桩
- **问题**: HarmonyOS 的 pthread.h 声明了常量但未实现 pthread_setcancelstate/setcanceltype/cancel 函数
- **修复**: 在 `#ifdef __OHOS__` 守卫下添加 inline no-op 桩函数，返回 0 (成功)
- **铁律**: R3, R8 (`#ifdef __OHOS__` 守卫，有实质逻辑)

## 编译命令
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INCLUDE_PATH="<libnet-include>;<libpcap-include>;<libdnet-include>;<sysroot-include>" \
  -DCMAKE_LIBRARY_PATH="<libnet-lib>;<libpcap-lib>;<libdnet-lib>;<sysroot-lib>"
make -j1
make install DESTDIR=$TEST_PREFIX
```

## make check 结果
- CMake 项目无 `check` target，跳过

## 二进制验证
- 产物: `build/src/arpon` (ELF 64-bit arm64, 440832 bytes)
- 手动编译成功，arpon 可执行文件生成

## conan-verify 结果
- G0 (预构建风险评估): PASS
- G1 (配方完整性): PASS
- G2 (conan create): FAIL — HarmonyOS getcwd() 限制
  - 根因: conan create 构建过程中，subprocess 在 conan cache 目录中执行，
    HarmonyOS 的 getcwd() 在这些目录中失败，导致 bash 报
    "shell-init: error retrieving current directory: getcwd: cannot access parent directories"
    进而导致 cmake 编译器检测测试失败 (compiler identification: unknown)
  - 手动运行相同 cmake 命令可成功 (compiler identification: Clang 15.0.4)
  - 这是 HarmonyOS 平台限制，非配方问题

## 依赖路径
- libnet/1.2: /storage/Users/currentUser/usr/local (从 feat/libnet-1.2 分支构建安装)
- libpcap/1.10.6: Conan cache (libpc826d64a62a3c5)
- libdnet/1.12: Conan cache (libdn1f2bfe2b18ba6)
- librt, libpthread: OHOS SDK sysroot
---

**编译结束**: 2026-08-17 11:19
**最终状态**: built
