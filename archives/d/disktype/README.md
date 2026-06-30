# disktype — 磁盘/磁盘镜像内容格式检测工具

## 简介

disktype 是一个检测磁盘或磁盘镜像内容格式的实用工具。它可以识别常见的文件系统、分区表和引导代码。程序使用 C 语言编写，设计为可在任何现代 Unix 系统上编译。它自包含，通常不需要特殊库或头文件。

## 识别格式

- **文件系统**: FAT12/FAT16/FAT32, NTFS, HPFS, HFS, HFS Plus, ISO9660, ext2/ext3, Minix, ReiserFS, Reiser4, Linux romfs/cramfs/squashfs, UFS, SysV FS, JFS, XFS 等
- **分区表**: DOS/PC, EFI GPT, Apple, Amiga, ATARI, BSD disklabel, Linux RAID/LVM, Solaris
- **压缩格式**: gzip, compress, bzip2（会自动解压分析内部内容）
- **归档格式**: tar, cpio, bar, dump/restore
- **磁盘镜像**: Raw CD (.bin), Virtual PC, Apple UDIF, Linux cloop
- **引导加载器**: LILO, GRUB, SYSLINUX, ISOLINUX, Linux kernel, FreeBSD loader 等

## OpenHarmony 适配要点

- **构建系统**: 纯 Makefile（无 configure 脚本，无 install/check 目标）
- **编译器覆盖**: 必须使用 `CC=clang`（Makefile 默认 gcc）
- **平台检测**: `uname` 返回 "HarmonyOS"，Makefile 无法自动启用 USE_IOCTL_LINUX，需手动添加 `CPPFLAGS="-DUSE_IOCTL_LINUX"`
- **G0 验证**: 使用 `hints/clean-verify-hints.yaml` 自定义构建和安装命令（因 CPPFLAGS 多参数不能用 configure_options 列表传递）
- **手动安装**: Makefile 无 install 目标，需手动 cp 二进制和 man 页
- **依赖**: 无（自包含，不需要外部库）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 9 | published | 2026-06-15 | 编译通过，功能验证10项全部PASS |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- disktype 9
```

## 使用方法

```bash
disktype <设备/文件>...
```

disktype 不接受选项参数，只接受文件或设备路径。对每个参数依次分析并输出格式信息。对压缩文件和磁盘镜像会递进分析内部内容。

## 示例输出

```
$ disktype disktype-9.tar.gz
--- disktype-9.tar.gz
Regular file, size 42.78 KiB (43809 bytes)
gzip-compressed data
  GNU tar archive
```
