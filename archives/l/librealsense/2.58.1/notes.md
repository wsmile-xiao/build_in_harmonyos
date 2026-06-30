# librealsense 2.58.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: **retrying** (第二次尝试，应用平台适配补丁)

## 第一次编译结果（失败）

**编译失败** - 平台兼容性问题

---

**编译开始**: 2026-05-26 17:55:00
**编译结束**: 2026-05-26 17:56:00
**最终状态**: failed

### 失败原因

1. **libusb 平台不支持**: CMakeLists.txt 直接拒绝 HarmonyOS
2. **系统头文件冲突**: sockaddr_storage 重定义
3. **缺少 netlink 定义**: sockaddr_nl, NETLINK_ROUTE 等缺失
4. **依赖 libudev**: HarmonyOS 不支持

## 第二次编译尝试（应用补丁）

### 补丁策略 (0001-harmonyos-platform-support.patch)

| 问题 | 解决方案 |
|------|----------|
| libusb 不识别 HarmonyOS | 修改 external_libusb.cmake，PATCH_COMMAND 中将 HarmonyOS 视为 Linux |
| libudev 依赖 | 禁用 LIBUSB_ENABLE_UDEV，使用 linux_netlink 后端 |
| network-adapter-watcher 需要 netlink | 添加 `__OHOS__` 宏，禁用该功能编译 |
| v4l2 后端依赖 libudev | 强制使用 RSUSB_BACKEND |

### 补丁文件位置
- `archives/l/librealsense/patches/0001-harmonyos-platform-support.patch`

### 关键编译选项
```bash
cmake .. \
    -DCMAKE_SYSTEM_NAME=HarmonyOS \
    -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
    -DFORCE_RSUSB_BACKEND=ON \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_GRAPHICAL_EXAMPLES=OFF \
    -DBUILD_TOOLS=OFF
```

---

**编译结束**: 2026-05-26 19:20
**最终状态**: built

---

## 编译成功

### 产物列表

| 文件 | 大小 | 说明 |
|------|------|------|
| librealsense2.so | 16.6 MB | 主动态库 |
| librealsense-file.a | 3.8 MB | 静态库 |
| librsutils.a | 1.6 MB | 工具静态库 |
| librs_lz4.a | 119 KB | LZ4 压缩库 |

### 补丁列表（5个）

1. **0001-CMake-external_libusb.cmake.patch** - libusb 平台适配
2. **0002-CMake-json-download.cmake.in.patch** - JSON 下载镜像
3. **0003-CMake-unix_config.cmake.patch** - 强制 RSUSB_BACKEND
4. **0004-CMakeLists.txt.patch** - 添加 __OHOS__ 宏
5. **0005-network-adapter-watcher.cpp.patch** - 禁用 netlink 功能

### 遇到的问题及解决

| 问题 | 解决方案 |
|------|----------|
| libusb 不识别 HarmonyOS | PATCH_COMMAND 中将 HarmonyOS 视为 Linux |
| sockaddr_storage 重定义 | 手动处理，避免 linux/netlink.h |
| 缺少 libudev | 强制 RSUSB_BACKEND |
| 缺少 netlink 定义 | 添加 __OHOS__ 禁用相关功能 |

### 知识沉淀

- librealsense 在 HarmonyOS 上需要强制使用 RSUSB_BACKEND
- libusb-cmake 需要 PATCH_COMMAND 将 HarmonyOS 视为 Linux
- __OHOS__ 宏可用于禁用 Linux 特有功能

---

## 预编译包（已生成）

| 文件 | 大小 | 说明 |
|------|------|------|
| librealsense-2.58.1-ohos-aarch64.tar.gz | 25.0 MB | 正式预编译包 |
| librealsense-2.58.1-ohos-aarch64-debug.tar.gz | 5.5 MB | 调试符号包 |

**路径**: `archives/l/librealsense/2.58.1/packaging/`

---

**最终状态**: published
