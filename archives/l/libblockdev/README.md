# libblockdev

## 简介
libblockdev 是一个用于操作块设备的库，采用插件化架构，支持 LVM、Btrfs、MD RAID、Swap、Loop 等多种块设备操作。

## OHOS 适配
- autotools 构建，需 30 个补丁修复 config.guess、configure umask、Makefile.in 等
- 仅启用 loop 插件（`--with-loop`），其余 13 个插件全部 `--without-*` 禁用
- 鸿蒙无原生 libudev/libkmod，创建 stub 库兼容 dlopen 加载
- bd_init() 因 kmod stub 循环依赖会卡住，建议使用 bd_loop_init() 单独初始化
- 需 glib 依赖：`-lintl -lpcre2-8 -lffi` 等链接库

## 依赖
- glib-2.0
- libudev (stub)
- libkmod (stub)
- libbytesize
- libmount (from util-linux)

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libbd_utils.so*
ls -la $HOME/usr/local/lib/libbd_loop.so*
# 验证插件加载
pkg-config --modversion libblockdev
```

## 参考
- 主页: https://github.com/storaged-project/libblockdev
- 源码: https://github.com/storaged-project/libblockdev/releases/tag/3.4.0