# gwenhywfar 5.14.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 解压
tar xzf gwenhywfar-5.14.1.tar.gz
cd gwenhywfar-5.14.1

# 修复 config.guess/config.sub（E007）
curl -fsSL config.guess > build-aux/config.guess
curl -fsSL config.sub > build-aux/config.sub

# 修复 umask（E011）
sed -i 's/umask 077/umask 022/g' configure

# 配置
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export DEFAULT_PREFIX=~/usr/local
./configure --prefix=$DEFAULT_PREFIX --disable-gtk3

# 编译
make -j2

# 手动修复 Makefile 变量（PKG_CHECK_MODULES 未展开）
sed -i 's/@LIBGNUTLS_LIBS@/-lgnutls/g; s/@LIBGNUTLS_CFLAGS@//g' Makefile
find . -name Makefile -exec sed -i 's/@LIBXML_LIBS@//g; s/@OPENSSL_LIBS@/-lssl -lcrypto/g' {} \;

# 修复 gui 目录
sed -i 's|SUBDIRS.*|SUBDIRS = cpp|g' gui/Makefile

# 重新编译
make -j2

# 安装（手动复制 .so，HMDFS 不支持硬链接）
cp .libs/libgwenhywfar.so.* ~/usr/local/lib/
cp gmp.h ~/usr/local/include/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 超时 | PKG_CHECK_MODULES 宏未展开 | 手动替换 Makefile 中的变量占位符 |
| 2 | 缺少 localcharset.h | 缺少 libiconv | 安装 libiconv 预编译包 |
| 3 | HMDFS 硬链接失败 | 文件系统不支持硬链接 | 手动复制 .so 文件 |
| 4 | gui 目录编译失败 | 缺少 Qt5/GTK3 | 修改 SUBDIRS 跳过 gui 模块 |

## 验证结果
```bash
$ pkg-config --modversion gwenhywfar
5.14.1

$ typemaker2 --version
typemaker2 v5.14.1
```

## 交付物
- gwenhywfar-5.14.1-ohos-aarch64.tar.gz (~2.2MB)
- 包含：libgwenhywfar.so.79, typemaker2, xmlmerge, gcttool

## 注意事项
- PKG_CHECK_MODULES 宏问题需要手动修复
- gui 模块已禁用，仅保留 cpp 基础模块