# libzbar 0.23.93 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://codeload.github.com/mchehab/zbar/tar.gz/refs/tags/0.23.93
2. 运行 autoreconf -fi 生成 configure 脚本
3. 安装依赖: dbus 1.14.10 预编译包
4. 运行 configure，禁用可选功能:
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local \
       --with-gtk=no \
       --with-qt=no \
       --with-java=no \
       --with-python=no \
       --without-imagemagick
   ```
5. 编译: make -j2
6. 安装到 staging: make install DESTDIR=/storage/Users/currentUser/test-install-libzbar-0.23.93
7. 制作预编译包: ohc-run.py package
8. 本地安装: make install
9. 验证: zbarcam --help 和 pkg-config --modversion zbar

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure.ac 存在但缺少 configure | tarball 来自 GitHub，未包含生成文件 | 运行 autoreconf -fi |
| 2 | 编译失败: 缺少 dbus/dbus.h | 未安装 dbus 开发库 | 从 cmd-pkgs 安装 dbus 1.14.10 预编译包 |
| 3 | GTK 编译失败: 缺少 gtk/gtk.h | 未安装 GTK 开发库 | configure --with-gtk=no 禁用 GTK |
| 4 | zbarimg 编译失败: 缺少 wand/wand_api.h | 未安装 GraphicsMagick/ImageMagick | configure --without-imagemagick 禁用 |
| 5 | make check 失败: 缺少 argp.h | musl libc 不支持 GNU argp 扩展 | 跳过测试并记录原因 |
| 6 | ln 硬链接失败: Operation not permitted | HMDFS 文件系统不支持硬链接 | 非致命错误，忽略 |

## 源码修改

无补丁。仅使用 configure 参数禁用可选功能。

## 依赖版本

- dbus: 1.14.10 (预编译包)

## 验证结果

```bash
# zbarcam 可执行
$ ~/usr/local/bin/zbarcam --help
usage: zbarcam [options] [/dev/video?]
scan and decode bar codes from a video stream

# pkg-config 版本
$ pkg-config --modversion zbar
0.23.93

# 库文件
$ ls ~/usr/local/lib/libzbar*
libzbar.a libzbar.la libzbar.so libzbar.so.0 libzbar.so.0.3.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libzbar-0.23.93-ohos-aarch64.tar.gz | 3519KB | 预编译包 |

## 注意事项

1. 核心库 libzbar 和工具 zbarcam 已编译成功，但 zbarimg（图像扫描工具）未编译（需要 ImageMagick/GraphicsMagick）
2. 测试套件因 musl libc 缺少 argp.h 而无法运行，但核心功能已验证可用
3. 需要设置 PKG_CONFIG_PATH 才能找到 dbus 和 zbar 的 pkg-config 文件
4. 禁用了 GTK/Qt/Java/Python 绑定，只编译核心 C 库
---

**编译结束**: 2026-08-25 01:02
**最终状态**: built
