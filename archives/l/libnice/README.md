# libnice

libnice 是一个实现了 ICE (Interactive Connectivity Establishment) 协议的开源库，用于 NAT 穿透，支持 STUN 和 TURN 协议。

## 功能概述

- ICE 协议完整实现（RFC 5245）
- STUN 协议支持（RFC 5389）
- TURN 协议支持（RFC 5766）
- UDP 和 TCP 传输支持
- 与 GLib 主循环集成
- 支持 IPv4 和 IPv6

## OHOS 适配要点

### 关键依赖要求

- **glib 必须使用动态链接版本**：预编译的 glib 2.88.0 使用静态链接 libintl（定义 `G_INTL_STATIC_COMPILATION`），会导致 `g_libintl_xxx` 符号未定义错误。必须使用 glib 2.84.0 动态链接版本。

### 编译器配置

- **必须设置 CC 环境变量**：`CC=/data/service/hnp/bin/clang`
- **必须设置 CXX 环境变量**：`CXX=/data/service/hnp/bin/clang++`
- **必须设置 AR 环境变量**：`AR=/data/service/hnp/bin/llvm-ar`

meson 构建系统无法自动找到鸿蒙 SDK 的编译器，需要显式设置环境变量。

### 构建命令

```bash
export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/data/service/hnp/bin/llvm-ar
meson setup builddir --prefix=$HOME/usr/local
ninja -j2
DESTDIR=$TEST_PREFIX ninja -C builddir install
```

## 依赖关系

### 编译依赖

- glib >= 2.44（必须动态链接版本）
- openssl >= 1.0.0
- pcre2
- libffi
- gettext

### 运行依赖

- glib（动态链接版本）
- openssl
- pcre2
- libffi
- gettext

## 参考资料

- 官网：https://nice.freedesktop.org
- 源码仓库：https://gitlab.freedesktop.org/libnice/libnice
- ICE 协议：RFC 5245
- STUN 协议：RFC 5389
- TURN 协议：RFC 5766