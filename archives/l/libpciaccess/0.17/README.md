# libpciaccess 0.17 for HarmonyOS/OpenHarmony (aarch64)

## 概述

libpciaccess 是 X.Org 项目的 PCI 设备访问库，提供跨平台的 PCI 设备信息查询接口。本配方为 HarmonyOS/OpenHarmony (aarch64) 平台提供 Conan 构建与依赖管理。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libpciaccess |
| 版本 | 0.17 |
| 下载地址 | https://xorg.freedesktop.org/releases/individual/lib/libpciaccess-0.17.tar.xz |
| 官方文档 | https://gitlab.freedesktop.org/xorg/lib/libpciaccess |

## 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | Meson |
| 编译器 | Clang 15 (OHOS) |
| 平台 | aarch64-linux-ohos |
| 默认产物 | 静态库 lib/libpciaccess.a（`shared=True` 可切共享库） |

## 产品列表

| 类型 | 文件 |
|------|------|
| 库 | lib/libpciaccess.a（或 libpciaccess.so.0.11.1） |
| 头文件 | include/pciaccess.h |
| pkg-config | lib/pkgconfig/pciaccess.pc |

> 上游 0.17 的 meson 目标 `scanpci` 未声明 `install: true`，故该工具随库构建但不进入包产物（0.19 起上游才提供 `install-scanpci` 选项）。

## 使用方法

```bash
# 安装到 Conan 缓存
conan install --requires=libpciaccess/0.17 -pr:h=<ohos-aarch64 profile> --build=missing

# CMake 消费
find_package(libpciaccess REQUIRED)
target_link_libraries(my_target libpciaccess::libpciaccess)
```

## 依赖

- zlib/1.3.1（gzip 压缩 pci.ids 数据库读取支持，`-Dzlib=enabled` 强制开启）

## 适配说明

- `patches/0001-ohos-backend.patch`：让 meson 将 harmonyos/ohos 视为 linux 选择 sysfs 后端源文件；`shared_library()` 改为 `library()` 以遵循 `default_library` 选项
- 上游 0.17 无 meson test() 注册（`meson test` 输出 "No tests defined."），消费者测试见 test_package/

## 编译难度

🟡 中等 - meson 构建系统，单补丁

## 更新日期

2026-09-17
