# seatd

## 简介
seatd 是一个 seat 管理服务，用于替代 systemd-logind，提供对图形设备（如 GPU、输入设备）的访问控制。它是 libinput 的可选依赖。

## 功能
- 提供 seat（座位）管理，控制多用户对图形设备的访问
- 替代 systemd-logind，不依赖 systemd
- 支持 seatd 和 builtin 两种后端
- 提供 libseat 库供应用程序使用

## 编译版本
- 版本: 0.9.1
- 构建系统: meson
- 编译器: clang 15.0.4

## 编译选项
```bash
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dlibseat-logind=disabled \
  -Dman-pages=disabled \
  -Dwerror=false
```

## 依赖
- meson >= 0.60.0
- ninja
- clang

## 安装产物
- `seatd` - seatd 服务守护进程
- `seatd-launch` - seatd 启动器
- `libseat.so.1` - libseat 共享库
- `libseat.h` - libseat 头文件
- `libseat.pc` - pkg-config 文件

## 使用方法
```bash
# 启动 seatd 服务
seatd -u <user> -g <group>

# 使用 seatd-launch 启动应用
seatd-launch -- <command>

# libseat API
#include <libseat.h>
```

## HarmonyOS 适配说明
- 禁用 logind 支持（无 systemd/elogind）
- poller 测试超时（HarmonyOS poll 系统调用行为差异）
- CMSG_NXTHDR 宏有类型比较警告，需禁用 werror