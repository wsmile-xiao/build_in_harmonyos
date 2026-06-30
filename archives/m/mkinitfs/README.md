# mkinitfs

## 简介
mkinitfs 是 Alpine Linux 的 initramfs 生成工具，用于创建初始 RAM 文件系统镜像。

## OHOS 适配
- 需禁用 nlplug-findfs（OHOS 不提供），通过 `WITH_NLPLUG=0` 编译选项
- 纯 Makefile 构建，编译选项通过环境变量传入

## 依赖
- 无编译依赖（纯 shell 脚本 + C 工具）

## 参考
- https://github.com/alpinelinux/mkinitfs