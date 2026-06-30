# vulkan-loader 1.3.295 编译笔记

## 编译日期
2026-05-21

## 编译状态
✅ 编译成功

## 构建系统
CMake

## 关键问题与解决方案

### 问题1: CMake 不识别 HarmonyOS 平台 (E092)

**症状**:
```
CMake Error: System is unknown to cmake
CMAKE_SYSTEM_NAME = harmonyos
```

**根因**: CMake 构建系统不认识 HarmonyOS 作为目标平台，没有对应的 platform module。

**解决方案**: 根据 E092 知识库，设置 `CMAKE_SYSTEM_NAME=Linux`，让 CMake 将 HarmonyOS 视为 Linux 平台。HarmonyOS 基于 Linux 内核，CMake 的 Linux 平台模块可以直接使用。

**使用的 configure 参数**:
```bash
cmake -B build \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_WSI_XCB_SUPPORT=OFF \
  -DBUILD_WSI_XLIB_SUPPORT=OFF \
  -DBUILD_WSI_WAYLAND_SUPPORT=OFF \
  -DBUILD_WSI_DIRECTFB_SUPPORT=OFF
```

**说明**: 
- 源码中已有 HarmonyOS 支持代码（检查 CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS"），但由于 CMake 本身不认识此系统名，需要使用 Linux 作为系统名
- 关闭所有 WSI (Window System Integration) 支持，因为 HarmonyOS 无 X11/Wayland
- 编译成功生成 libvulkan.so.1.3.295

### 问题2: secure_getenv 函数缺失 (预扫描 PSCAN-MUSL-004)

**症状**:
```
-- Looking for secure_getenv - not found
-- Looking for __secure_getenv - not found
CMake Warning: Using non-secure environmental lookups.
```

**根因**: secure_getenv 是 glibc 扩展，musl 未实现

**影响**: 轻微，不影响编译成功，只是警告。OHOS 无 setuid 场景，环境变量安全性问题不严重。

## 源码修改记录

**本次编译无源码修改**。所有问题通过 CMake 参数配置解决，未修改任何源码文件。

## 编译产物

- `libvulkan.so.1.3.295` (542K)
- `libvulkan.so.1` (软链接)
- `libvulkan.so` (软链接)

## 验证步骤

1. CMake 配置成功 ✅
2. make 编译成功 ✅
3. make install DESTDIR=$TEST_PREFIX 成功 ✅
4. 质量门禁 G1-G4 通过 ✅

---
*编译笔记 · 2026-05-21*