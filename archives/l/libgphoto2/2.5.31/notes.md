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

**编译结束**: 2026-08-27 11:24
**最终状态**: built


---

# Conan 适配 v2（2026-09-17）

## 变更要点（相对 8-27 conan v1 配方）

1. **shared=True 默认**：上游 `LT_INIT([disable-static dlopen])`（configure.ac 注释
   "Disable building static library, as no one uses it anyway"）——camlibs/iolibs 是
   dlopen 模块，静态构建产物运行时无法加载任何相机驱动（`Found 0 camera drivers`，
   实测上游 test suite 49 项全挂）。v1 配方 `--enable-static --disable-shared` 违背
   上游设计，v2 改为 shared 构建（本库非系统同名库，符合动态默认策略）。
2. **USB 启用**（取消 `--without-libusb1`）：libusb/1.0.27 已发布到制品仓，通过
   显式 `LIBUSB1_CFLAGS/LIBUSB1_LIBS` 传入（libusb 包自带 .pc 的 prefix=/usr/local
   与 conan 缓存布局不符，pkg-config 不可靠）。iolibs: usb1 + usbdiskdirect + usbscsi
   （host=aarch64-unknown-linux-ohos 匹配 `*-linux*` 分支）。
3. **libjpeg-turbo/3.2.0 依赖**：ptp2(CHDK)/ax203/jl2005c/sipix camlib 需要 JPEG
   解码（GP_LIBJPEG 显式变量模式，链接失败即中止——不会静默裁剪）。
4. **libexif 检测修复**：v1 构建中 HAVE_LIBEXIF 未定义（libexif .pc prefix=/ 导致
   pkg-config 给出错误 -I/include 路径）。v2 用显式 `LIBEXIF_CFLAGS/LIBEXIF_LIBS`
   传入，libgphoto2 与 libgphoto2_port 双双启用 EXIF。
5. **移除 popt/zlib 依赖**：libgphoto2 源码与 configure.ac 均无引用（popt 是 gphoto2
   CLI 的依赖；zlib 完全未用）——v1 属误带。
6. **runenv_info 导出 CAMLIBS/IOLIBS**：conan 构建的编译期默认模块目录（prefix=/
   → /lib/libgphoto2/2.5.31）在 conan 缓存布局下不存在；消费者 conanrun 环境通过
   CAMLIBS/IOLIBS 环境变量指向真实模块目录（libgphoto2 运行时优先读这两个变量）。

## 验证结果（2026-09-17，本机 OHOS aarch64）

- `conan create`（ohos-aarch64 profile, --build=missing）：见下方实测记录
- test_package（gp_context_new/gp_camera_new API 消费者测试）
- `gphoto2 --version` 下游联动验证：camlibs/iolibs 可加载（详见 PR #4975）

## 验证结果（2026-09-18，补丁重命名后复验）

- `conan create`（ohos-aarch64 profile, --build=missing）：**PASS**（0004-0006 补丁集，
  与先前 0001-0003 内容字节级等价，仅文件名变更）
- test_package 输出：`gphoto2 context and camera created successfully` — PASS

## Conan 配方补丁（0004-0006，紧凑重制版）

- `0004-config.guess-ohos.patch`: E007 OpenHarmony 平台识别（替代旧 0001 手工全量补丁）
- `0005-config.sub-ohos.patch`: E007 ohos-linux 三元组支持（替代旧 0002 手工全量补丁）
- `0006-configure-tmpdir.patch`: config.status 临时文件走 TMPDIR（HMDFS 权限修复）
- 旧 `0001`/`0002`/`0003-auto-m4-pkg.m4` 为 2026-06 手工构建期补丁，仅作历史存档保留，
  conan 配方不引用（release tarball 自带预生成 configure，无需 pkg.m4）
