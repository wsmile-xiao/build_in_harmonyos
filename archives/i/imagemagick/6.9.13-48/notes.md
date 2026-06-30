# imagemagick 6.9.13-48 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 设置 CONFIG_SHELL 防止 print 命令问题
export CONFIG_SHELL=/data/service/hnp/bin/bash

# 安装委托库
# libjpeg-turbo 3.1.4.1、xz 5.6.2 通过 cmd-pkgs 预编译包安装

# 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build imagemagick 6.9.13-48

# 应用 config.guess/config.sub 补丁
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config/config.guess config/config.sub

# configure
$CONFIG_SHELL ./configure --prefix=$DEFAULT_PREFIX \
  --without-x --without-tiff --without-jbig --without-djvu \
  --without-webp --without-wmf --without-fftw --without-xml \
  --without-gslib --without-pango --disable-openmp --disable-opencl \
  HELP2MAN=/bin/true MAKEINFO=/bin/true

# 编译
make -j2

# 安装（DESTDIR staging）
make install DESTDIR=$TEST_PREFIX HELP2MAN=/bin/true

# 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package imagemagick 6.9.13-48
python3 $SKILL_ROOT/scripts/ohc-run.py package imagemagick 6.9.13-48 --debug
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied 创建 subs1.awk | HMDFS 上 umask 077 创建的目录权限0700导致无法写入 | 移除 configure 中 umask 077（E050） |
| 2 | config.status `print: command not found` | toybox sh 不支持 print 命令 | 设置 CONFIG_SHELL=/data/service/hnp/bin/bash |
| 3 | configure 无法识别 OHOS 平台 | config.guess/config.sub 缺少 OHOS triplet | 使用 patch-autotools-ohos.pl 补丁（E007） |
| 4 | make check 34 个 ERROR | tap-driver.sh 使用 `>&3`(fd 3)，OHOS shell 不支持 | 平台限制，非软件bug |

## 源码修改

| 文件 | 修改内容 | 补丁 |
|------|---------|------|
| config/config.guess | 添加 __OHOS__ LIBC 检测 + HarmonyOS 系统识别 | 0001-config.guess.patch |
| config/config.sub | 添加 ohos-linux triplet | 0002-config.sub.patch |
| configure | 移除 umask 077（mktemp 和 mkdir） | 0003-configure.patch |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libjpeg-turbo | 3.1.4.1 | cmd-pkgs 预编译 |
| xz (lzma) | 5.6.2 | cmd-pkgs 预编译 |
| lcms2 | unknown | 系统预装 |
| libpng | 1.6.43 | 系统预装 |

## 验证结果

```bash
$ convert --version
Version: ImageMagick 6.9.13-48 Q16 aarch64
Features: Cipher DPC
Delegates (built-in): jpeg lcms lzma
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| imagemagick-6.9.13-48-ohos-aarch64.tar.gz | 38MB | 预编译包（release） |
| imagemagick-6.9.13-48-ohos-aarch64-debug.tar.gz | 2.8MB | 调试符号包 |

## 注意事项

- ImageMagick 6 是 legacy 版本，与 v7 是不同的源码仓库
- make check 的 tap-driver.sh 在 OHOS 上不可用（`>&3` 不支持），测试框架需替代方案
- CONFIG_SHELL 必须设为 bash，否则 config.status 中 print 命令会报错

---

**编译结束**: 2026-05-25
**最终状态**: built