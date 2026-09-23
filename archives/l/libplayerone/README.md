# libplayerone

## 软件描述

libplayerone 是 Player One Astronomy (POA) 天文相机的官方 C SDK，用于通过
USB 访问 POA/ONE/ZWO 系列天文相机：

- 相机枚举与属性查询（`POAGetCameraCount` / `POAGetCameraProperties`）
- 相机控制（`POAOpenCamera` / `POAInitCamera` / 曝光 / 传感器模式）
- 图像采集（`POAImageReady` / `POAGetImageData`）
- 单头文件接口（`PlayerOneCamera.h`，`POACAMERA_API` 导出宏）

**注意**：本库是厂商预编译的闭源二进制包（按架构分发 `.bin`），不含可编译
源码；需要物理相机连接才能实际运行。本仓库交付的是 OHOS aarch64 可用的
安装包（头文件 + 厂商 aarch64 共享库 + udev 规则）。

## 版本信息

- 当前版本: 3.1.0（Player One Astronomy 官方 SDK，2022-12-18 构建）
- 官方主页: https://libplayerone.org/
- 源码: https://salsa.debian.org/debian-astro-team/libplayerone
  （上游快照 tag `upstream/3.1.0+20221218103507`；
  GitHub 镜像 indilib/indi-3rdparty 的 libplayerone/ 子目录）

## OHOS 适配

- 上游无构建目标：CMakeLists 仅 `add_library(PlayerOneCamera SHARED
  IMPORTED)` + `install_imported`，配方按其安装语义交付
- 厂商 `.bin`（SONAME `libPlayerOneCamera.so.3`）重命名为 SONAME 名安装到
  `lib/`，并建 `libPlayerOneCamera.so` 符号链接使 `-lPlayerOneCamera` 可用
- 头文件安装到 `include/libplayerone/`，下游 `#include
  <PlayerOneCamera.h>` 或 `#include "PlayerOneCamera.h"` 均可
- udev 规则随包交付（`lib/udev/rules.d/`），供 USB 设备权限配置参考
- `package_type = "shared-library"`，`shared` option 默认 True（厂商只发
  共享库）；`package_id` 剔除 compiler/build_type（预编译二进制与构建工具链
  无关），仅 arch 影响内容

## 依赖说明

- 运行时依赖 `libusb/1.0.27`（厂商 `.so` NEEDED `libusb-1.0.so.0`，
  USB 通信）
- 无构建期依赖（无编译步骤）

## 测试

test_package 采用下游消费方式验证（厂商库无法在无相机/无 dlopen 沙箱中
运行）：

1. 头文件：声明核心 API（POAGetAPIVersion/POAGetCameraCount/
   POAOpenCamera/POAGetCameraProperties）且使用 POACAMERA_API 导出宏
2. 厂商 .so：ELF64 AArch64 DYN，SONAME 与文件名一致，NEEDED
   libusb-1.0.so.0，导出核心 API 符号
3. 下游链接：OHOS clang 交叉编译引用核心 API 的探针（lpo_probe.c）并链接
   厂商 .so，断言产物含 NEEDED libPlayerOneCamera.so.3 且导出
   lpo_probe_version（R34 下游可用性证明）
