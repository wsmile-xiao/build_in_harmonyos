# zbar 0.23.93 适配笔记

## 编译环境
- 构建系统: autotools (需要 autoreconf)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 (GitHub mchehab/zbar 0.23.93 tag)
2. 移除 AM_GNU_GETTEXT/AM_ICONV (autopoint 不可用)
3. autotools.autoreconf() 生成 configure (automake/1.18 via tool_requires from ohpcd)
4. 修补 config.guess/sub (E007，autoreconf 安装的版本已包含)
5. 修复 configure umask 077→022 (E011)
6. 设置 PKG_CONFIG_PATH 指向 ImageMagick
7. ./configure --prefix=$DEFAULT_PREFIX --without-x --without-dbus --without-qt --without-gtk --without-python --without-java
8. make -j2
9. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autopoint 不可用 | gettext 未安装 | 移除 AM_GNU_GETTEXT/AM_ICONV |
| 2 | config.guess 不识别 HarmonyOS | E007 | autoreconf 安装的版本已包含 |
| 3 | configure umask 077 权限拒绝 | E011 | sed umask 022 |
| 4 | ImageMagick .la 文件路径错误 | conan 安装 prefix 不正确 | sed 修复 libdir |
| 5 | make check 缺少 argp.h | OHOS 无 argp.h | 不影响核心库和 zbarimg |
| 6 | CI 缺少 automake/aclocal | CI worker 未安装 automake | 预生成 autotools 文件 (prebuilt.tar.gz) |

## 补丁

| 文件 | 修改 | 说明 |
|------|------|------|
| 0001-Makefile.am.patch | 移除 po/ 目录引用 | autopoint 不可用 |
| 0002-configure.ac.patch | 移除 gettext 宏 | autopoint 不可用 |

## 依赖版本

- imagemagick/7.1.2.29

## 产物

- zbarimg: 条码/二维码图像识别命令行工具
- zbarcam: 视频流条码识别工具
- libzbar: 条码识别核心库 (.a/.so)
- 支持的条码: EAN, DataBar, Code128, Code93, Code39, Codabar, I25, QR Code, SQ Code

## 验证结果

```
conan create: PASS (G0-G4 + L2/L4/L5)
test_zbar: PASS - libzbar scanner created and configured
zbar version: 0.23.93
W3 CI 模拟: PASS
```

---

**编译结束**: 2026-08-06 22:30
**最终状态**: built
