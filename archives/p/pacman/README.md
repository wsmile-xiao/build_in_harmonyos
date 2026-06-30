# Pacman - Package Manager

## 简介

pacman 是 Arch Linux 的官方包管理器，提供了完整的包管理功能，包括安装、删除、查询、升级等操作。

## 功能特性

- 包安装与删除
- 包依赖管理
- 包查询与搜索
- 包升级与同步
- 本地包数据库管理
- 包签名验证（需 GPGME）

## 编译版本

- **版本**: 7.1
- **构建系统**: Meson
- **平台**: OpenHarmony (OHOS) aarch64

## 依赖

- openssl (签名验证)
- curl (网络下载)
- libarchive (包解压)
- gettext (国际化)
- xz (lzma 压缩)

## 安装

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- pacman 7.1
```

## 使用示例

```bash
# 查看版本
pacman --version

# 查询包信息
pacman -Qi <package_name>

# 安装包
pacman -S <package_name>

# 删除包
pacman -R <package_name>
```

## 注意事项

- GPGME 支持未启用，签名功能受限
- 需要正确配置 pacman.conf
- makepkg 依赖 GNU bash

## 来源

- 官方网站: https://archlinux.org/pacman/
- 源码仓库: https://gitlab.archlinux.org/pacman/pacman