# libfuse for HarmonyOS (OpenHarmony)

## 概述

libfuse (FUSE 3.x) — Filesystem in Userspace 在 HarmonyOS/OpenHarmony (aarch64) 
上的编译指南和适配记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libfuse (fuse3) |
| 版本 | 3.18.2 |
| 下载地址 | https://github.com/libfuse/libfuse/releases/download/fuse-3.18.2/fuse-3.18.2.tar.gz |
| 官方文档 | https://github.com/libfuse/libfuse |
| 许可证 | LGPL-2.1 (library), GPL-2.0 (utilities) |
| 构建系统 | Meson |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| SDK | ohos-sdk 26.0.0.18 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| Meson | 1.11.1 |
| Ninja | 1.13.1 |

## 已适配版本

- [3.18.2](./3.18.2/)

## 关键适配点

1. **host_machine.system()**: OHOS 上返回 'harmonyos'，需要 patches 处理
2. **mount.c vs mount_bsd.c**: OHOS 应使用 Linux 风格的 mount.c
3. **pthread_cancel/pthread_setcancelstate**: OHOS libc 未提供，需要补丁
4. **dl/rt 库**: OHOS 中已集成到 libc，无需额外链接
5. **udev**: OHOS 上不支持，需禁用 udev 相关功能

## 经验总结

1. OHOS 的 meson 交叉编译需要正确设置 cross file
2. validate() 必须加入 "OHOS" 到接受的操作系统列表
3. 构建命令中必须禁用 examples/utils/tests/useroot
4. test_package 应调用实际的 libfuse API 以验证链接正确性
