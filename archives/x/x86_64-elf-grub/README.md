# x86_64-elf-grub

`x86_64-elf-grub` 是面向 `x86_64-elf` 裸机目标的 GNU GRUB 交叉构建工具集。包内命令运行在 HarmonyOS PC（AArch64）宿主上，用于生成和检查 x86_64 EFI/GRUB 镜像，不会在宿主上执行 x86_64 目标代码。

## 功能概述

- 生成 `x86_64-efi` GRUB core image。
- 检查 Multiboot、EFI 及其他 GRUB 支持的文件格式。
- 校验 GRUB 配置脚本。
- 创建和修改 GRUB environment block。
- 随包安装 `x86_64-efi` 平台模块和数据文件。

## OHOS 适配

- 宿主工具使用 Conan profile 中的 HarmonyOS Clang 编译。
- 目标代码使用 Clang 前端的裸机三元组，并由已发布的 GNU
  `x86_64-elf-ld` 链接。
- `x86_64-elf-binutils/2.46.1` 提供目标链接和对象处理工具。
- `config.guess`、`config.sub` 增加 HarmonyOS/OHOS 识别。
- 预生成 `configure` 的两个临时目录掩码从 `077` 调整为 `022`，兼容 HMDFS。
- 生成的 `config.status` 统一通过 `/system/bin/sh` 执行，绕过 HMDFS noexec。
- 权威 Automake 输入先于 shipped `Makefile.in` 应用补丁，避免时间戳触发设备上
  不存在的 Automake（E041）。
- 受限进程不可枚举根目录时，只对 hostfs 的 `/` 身份探测放行 `EACCES`，其他错误与
  实际文件校验保持原样（E226 知识草稿随本软件 PR 提交）。
- 文档生成工具在交叉构建中禁用，安装时显式清空 `man_MANS`（E217 知识草稿随本软件 PR 提交）。
- 包中保留 268 个运行模块 `.mod`，移除只供 GDB 使用的 `.module` 中间文件，
  并通过 prefix-map 清除构建缓存绝对路径。

## 依赖关系

- 编译依赖：`x86_64-elf-binutils/2.46.1`
- 运行依赖：无额外 Conan 运行库；宿主 C/C++ 运行时由 HarmonyOS 提供。

## 参考资料

- [GNU GRUB 官网](https://www.gnu.org/software/grub/)
- [GNU GRUB 源码下载](https://ftp.gnu.org/gnu/grub/)
