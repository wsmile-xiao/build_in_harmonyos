# dos2unix 7.5.4 编译说明

## 概述

dos2unix/unix2dos 是 DOS/MAC 与 Unix 文本格式转换工具，版本 7.5.4，支持 Unicode UTF-16。

## 编译环境

- **平台**: HarmonyOS (aarch64)
- **编译器**: clang 15.0.4
- **构建系统**: Makefile (无 configure)

## 编译步骤

```bash
# 下载
curl -fSL -o dos2unix-7.5.4.tar.gz \
  "https://downloads.sourceforge.net/project/dos2unix/dos2unix/7.5.4/dos2unix-7.5.4.tar.gz"
tar -xf dos2unix-7.5.4.tar.gz && cd dos2unix-7.5.4

# 应用补丁
patch -p1 < patches/0001-disable-nls-and-fix-symlink-creation.patch

# 编译
make -j1 dos2unix unix2dos

# 安装
make -j1 install-bin prefix=$HOME/usr/local
```

## 适配说明

1. **禁用 NLS**: HarmonyOS 缺少 libintl/gettext，需禁用国际化支持
2. **软链接**: Makefile 默认 `ln -sf` 在部分目录受限，改为 `ln -s`

## 已知限制

- 不支持国际化（NLS 已禁用）
- 测试套件中 mac2unix/unix2mac 和 symlink 相关测试因 HarmonyOS 软链接限制失败
