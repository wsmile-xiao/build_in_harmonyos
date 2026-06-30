# libgphoto2 2.5.31 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **Init**: `python3 ohc-run.py init-build libgphoto2 2.5.31 --url=https://github.com/gphoto/libgphoto2/archive/refs/tags/v2.5.31.tar.gz`
2. **autoreconf**: Manual autoreconf -fi with explicit aclocal flags (-I auto-m4 -I gphoto-m4 -I pkg-config/aclocal)
3. **E007 Fix**: Patch config.guess/config.sub for OpenHarmony (aarch64-unknown-linux-ohos)
4. **libltdl**: Built libltdl from libtool 2.4.3a source (required prerequisite)
5. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --disable-nls --without-libusb1 LTDLINCL="-I$DEFAULT_PREFIX/include" LIBLTDL="-L$DEFAULT_PREFIX/lib -lltdl"`
6. **Build**: `make -j1` — SUCCESS
7. **Install**: `make install DESTDIR=$TEST_PREFIX` — SUCCESS
8. **Test**: `make check` — PASS
9. **Package**: `ohc-run.py package libgphoto2 2.5.31` — SUCCESS
10. **Install to local**: `make install` — SUCCESS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build找不到URL | GitHub tag format是v2.5.31而非libgphoto2-2.5.31 | 使用--url手动指定URL |
| 2 | autoreconf失败(PKG_CHECK_MODULES未定义) | pkg-config的pkg.m4未在aclocal搜索路径 | 复制pkg.m4到auto-m4/并手动aclocal |
| 3 | aclocal找不到gphoto-m4 | 路径在libgphoto2_port/gphoto-m4（HMDFS问题） | 复制到根目录gphoto-m4/ |
| 4 | configure失败(libltdl未找到) | 没有安装libltdl库 | 先从libtool源码构建并安装libltdl |
| 5 | config.guess不识别OpenHarmony | E007: GNU config.guess不含HarmonyOS分支 | 用patch-autotools-ohos.pl打补丁 |
| 6 | ltmain.sh缺失 | autoreconf未复制libtool的ltmain.sh | 手动从~/usr/local/share/libtool复制 |

## 源码修改

- `0001-auto-aux-config.guess.patch`: E007 OpenHarmony平台识别
- `0002-auto-aux-config.sub.patch`: E007 ohos-linux三元组支持
- `0003-auto-m4-pkg.m4.patch`: 添加pkg-config m4宏到项目本地

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libltdl | 2.4.3a | 从libtool源码构建 |
| libexif | 0.6.26 | 已安装 |
| popt | 1.16 | 已安装 |
| zlib | 1.3.1 | cmd-pkgs预编译包 |
| libusb-1.0 | - | 已安装但disabled |

## 验证结果

```bash
$ pkg-config --modversion libgphoto2
2.5.31
$ pkg-config --cflags libgphoto2
-I/storage/Users/currentUser/usr/local/include/gphoto2
$ pkg-config --libs libgphoto2
-L/storage/Users/currentUser/usr/local/lib -lgphoto2 -lm -lgphoto2_port -lm
$ pkg-config --modversion libgphoto2_port
0.12.2
$ sh auto-aux/config.guess
aarch64-unknown-linux-ohos
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgphoto2-2.5.31-ohos-aarch64.tar.gz | 6932KB | 预编译包（主） |
| libgphoto2-2.5.31-ohos-aarch64-debug.tar.gz | - | 预编译包（调试符号） |

## 注意事项

- USB IOLib已disabled(--without-libusb1)，因OpenHarmony libusb1 API差异
- NLS已disabled(--disable-nls)，避免gettext复杂性
- libltdl需先构建安装才能配置libgphoto2
- autoreconf需手动指定-I路径（pkg.m4和gphoto-m4）
- git checkout版本不含configure，需autoreconf生成

---
**编译结束**: 2026-06-04 03:19
**最终状态**: published
---

**编译结束**: 2026-06-04 03:20
**最终状态**: published
