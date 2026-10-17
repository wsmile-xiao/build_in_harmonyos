# libwebcam 0.2.5 适配笔记

## 概述

libwebcam 是 Linux UVC 项目的用户态库，通过 V4L2 扩展控制 UVC 摄像头。
同时构建 `uvcdynctrl` 命令行工具。

## 源码

- URL: https://deb.debian.org/debian/pool/main/libw/libwebcam/libwebcam_0.2.5.orig.tar.gz
- sha256: 3ca5199c7b8398b655a7c38e3ad4191bb053b1486503287f20d30d141bda9d41
- 这是 Debian pool 中的 pristine upstream .orig.tar.gz（SourceForge 官方发布）

## 构建系统

CMake (cmake_minimum_required 2.6)。

## 依赖

- **libxml2/2.15.3.1**：解析 UVC 控制映射 XML 文件（pkg_check_modules libxml-2.0）

## 补丁

### 0001-ohos-cmake-compat.patch

1. 将 `pkg_check_modules(LIBXML2 REQUIRED libxml-2.0)` 替换为 Conan 注入的
   `LIBXML2_INCLUDE_DIRS`/`LIBXML2_LIBRARIES` 缓存变量检查
2. 将无条件构建 shared+static 改为基于 `BUILD_SHARED_LIBS` 条件构建
3. 跳过 `try_compile` V4L2 探测，直接定义 `ENABLE_RAW_CONTROLS`
4. 移除上游 .pc 文件生成（Conan 管理依赖信息）

### 0002-uvcdynctrl-ohos.patch

1. 移除 uvcdynctrl 的 udev 规则/脚本绝对路径安装（`/lib/udev/...`）
2. man page gzip 改为非致命（OHOS toybox gzip 不支持 `--best`）
3. 移除 `link_directories`（使用 target-level linking）
4. 移除 man page 安装（gzip 可能失败导致 install 报错）

## 真机构建结果（2026-09-24）

- Profile: `ohos-aarch64-fixed`（注意：`ohos-aarch64` 的编译器路径 `/data/service/hnp/bin/clang` 不存在）
- 构建成功：`libwebcam.so` + `uvcdynctrl`
- test_package C API：3/3 通过（c_get_error_text 错误字符串表）
- 包 ID: `2bb16680d2b1ebc3ae66fc97c6ed3d2f2482d19c`

## 已知限制

- 实际使用需要物理 UVC 摄像头设备
- udev 规则已从打包中移除（OHOS 无 udev）
- dynctrl 数据文件（XML 控制映射）安装到 share/uvcdynctrl
- **uvcdynctrl 运行时 RPATH 问题**：二进制仍带构建树 RPATH `$ORIGIN/../libwebcam/`，
  导致 `uvcdynctrl --help` 无法找到 libwebcam.so。需要在补丁中用 `install_name_tool`
  或在 package() 中 patchelf 修正 RPATH。不影响 libwebcam.so 库本身。
- ELF 签名未执行（真机上 `/data/service/hnp/bin/binary-sign-tool` 路径待确认）
