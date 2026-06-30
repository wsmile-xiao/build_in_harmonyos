# efi-mkuki

> Tool to create UEFI Kernel Unified Image (UKI) for Linux kernels

## 简介

efi-mkuki 是一个用于创建 UEFI Kernel Unified Image（UKI）的工具。UKI 是一种将 Linux 内核、initramfs 和内核命令行组合为单一 EFI 可执行文件的标准格式，便于 UEFI 固件直接加载和启动。

## OHOS 适配要点

- Shell 脚本项目，无需编译
- 仅需安装到正确路径即可使用
- 验证: `efi-mkuki -V` 输出 `efi-mkuki 1.0.0`

## 参考

- [源码仓库](https://github.com/efi-mkuki/efi-mkuki)