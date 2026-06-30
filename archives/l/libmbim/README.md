# libmbim

Mobile Broadband Interface Model 库，用于 ModemManager 与移动宽带设备通信。

## 功能概述

- 提供 MBIM 协议的 GLib 绑定
- 支持与移动宽带调制解调器通信
- 提供 mbimcli 命令行工具

## OHOS 适配要点

1. **meson 编译器配置**：需设置 CC/CXX/AR 环境变量（绝对路径）
2. **E091 sockaddr_storage 问题**：
   - OHOS 内核 linux/socket.h 与 musl sys/socket.h 冲突
   - 需使用宏守卫 `#define sockaddr_storage __linux_sockaddr_storage`
3. **可选功能禁用**：
   - `-Dbash_completion=false`
   - `-Dintrospection=false`
   - `-Dman=false`

## 依赖关系

- glib-2.0 >= 2.56.0 (必需)
- meson >= 0.50

## 编译步骤

```bash
export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/data/service/hnp/bin/llvm-ar

meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dbash_completion=false \
  -Dintrospection=false \
  -Dman=false
ninja -C builddir
ninja -C builddir install
```

## 补丁说明

- 0001-0004: E091 sockaddr_storage 宏守卫补丁（4个文件需要修改）

## 参考资料

- 官网：https://www.freedesktop.org/wiki/Software/ModemManager/
- 源码：https://gitlab.freedesktop.org/mobile-broadband/libmbim