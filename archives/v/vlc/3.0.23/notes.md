# vlc 3.0.23 适配笔记（OHOS aarch64）

> 2026-09-25 · 2404_87638649 · 任务 vlc 3.0.23（平台任务 id=11723）

## 结论

**conan create 全绿**：libvlc/libvlccore + 283 插件 + vlc 二进制完整产出，
test_package（libvlc_new/version/release API）5/5 PASS。本机构建耗时约 9.5 分钟
（HMDFS 上 283 插件逐个 relink 是 install 阶段耗时主体）。

## 源码与裁剪

- 官方 tarball：https://get.videolan.org/vlc/3.0.23/vlc-3.0.23.tar.xz
  （sha256 e891cae6aa3ccda69bf94173d5105cbc55c7a7d9b1d21b9b21666e69eff3e7e0）
- autotools 构建，交叉 `--host=aarch64-linux-ohos`
- 裁剪：XCB/Wayland/X11/Qt/skins2/notify/ncurses/SDL/VDPAU/VAAPI/V4L2/DVB/
  decklink/macosx/wasapi/oss/alsa/pulse/jack/a52/lua/gnutls/gcrypt/classic-GL 全禁
- codec 全保留：ffmpeg(avcodec/avformat/swscale)+mad+ogg/vorbis/theora/flac/opus+
  dav1d/vpx/x264/x265+dvdnav+libass 字幕链

## 四个补丁（全部在干净 tarball 验证 patch -p1 可应用）

1. **0001 ohos-triplet**：config.guess 加 HarmonyOS case（注意补丁脚本生成的
   `GUESS=` 变量块无效，须 `echo ... ; exit ;;`）；config.sub 四处白名单
   （maybe_os 列表 + ohos-linux 分支 + OS 白名单 + kernel-os 验证列表）
2. **0002 capability-macros**（posix_close + pthread_cancel 合并）：configure.ac
   的 linux 分支 AC_CHECK_FUNCS 追加 posix_close/pthread_cancel/
   pthread_setcancelstate/pthread_testcancel 四函数链接探测——OHOS musl 头文件
   定义了 POSIX_CLOSE_RESTART/PTHREAD_CANCEL_* 宏但未实现函数（头/实现不同步），
   链接探测按符号存在性决定；源码侧 vlc_close/vlc_cancel/vlc_savecancel/
   vlc_restorecancel/vlc_testcancel 依据 HAVE_POSIX_CLOSE/HAVE_PTHREAD_CANCEL
   等 autoconf 能力宏分支，缺能力时走 POSIX 兼容 fallback（close(fd)/no-op）。
   R8 合规：不引入 __OHOS__ 平台宏，glibc/musl 主线等有能力平台行为不变
   （libvlc_new/release 实测正常——vlc 线程退出走 join 不依赖 cancel）
4. **0004 disable-classic-gl**：configure.ac AS_IF 守卫 + 预生成 configure 的
   两处 fallback 编译分支加 `host_os=linux-ohos` 短路（tarball configure 是
   autoconf 2.69 产物，autoconf 2.72 重生成 diff 巨大不可入补丁——**必须双文件
   patch**，只改 configure.ac 的话 CI 无 autoconf 场景下预生成 configure 仍是旧逻辑）

## conan 配方要点（踩坑记录）

- **PkgConfigDeps 生成 pc 的版本字段用包版本**（ffmpeg/4.4.8），vlc 要求
  libavcodec>=57.37.100（库 ABI 版本号）→ build() 里用包内原生 pc
  （lib/pkgconfig/libavcodec.pc，Version: 58.134.100）替换并**逐行重写路径**
  （原生 pc 的路径变量可能是构建期残留 b/<hash>/p——不要用字符串 replace 猜，
  逐行 prefix=/exec_prefix=/libdir=/includedir= 全部重写为 conan 包路径）
- **x264 同理**（conan pc Version: r3223，vlc 要求 >=0.148；原生 0.165.3223）
- **libogg 版本碎片**：flac(1.3.5)/libvorbis(1.3.6)/libtheora(1.3.6.2) 三方
  requires 互相冲突 → 顶层 `self.requires("libogg/1.3.6", force=True)`（另
  libopus/libvpx 与 ffmpeg 传递链冲突同理 force）
- **静态库传递依赖**：flac/vorbis 的 `Requires.private: ogg` 不被 pkg-config
  默认展开 → 提升公共 Requires；x265 静态库 Libs 补 -lc++
- **vlc 3.0 上游 bug**：fontconfig.c 只注入 -DHAVE_FONTCONFIG 不注入
  FONTCONFIG_CFLAGS（4.0 修复）→ freetype2.pc 的 Cflags 并入 fontconfig include
- **fribidi 头在 include/fribidi/ 子目录**，vlc `#include <fribidi.h>` 直引 →
  fribidi.pc Cflags 补子目录路径
- **opus 头在 include/opus/**，vlc `#include <opus.h>` 直引 → opus.pc
  includedir 改指 include/opus
- **libmad 检测不走 pkg-config**：configure 用 `--with-mad=PATH` +
  AC_CHECK_HEADERS/AC_CHECK_LIB → requirements 里取 package_folder 显式传
- **BUILDCC**：构建期工具（fourcc_gen）本机执行。本机即 aarch64 HarmonyOS，
  clang 默认 target 即本机 → `Environment().define("BUILDCC", CC)` 注入
  （Autotools.configure() 不支持 vars= 参数）
- **HMDFS umask 077（E011）**：configure/config.status 内嵌 umask 077 的
  mktemp -d 目录对构建进程不可写 → build() 里 `replace_in_file` sed 成 022
- **补丁后 automake 重建链**：0004 改 configure.ac → 比 aclocal.m4 新 →
  CI 触发 aclocal-1.16（不存在 + @am_AUTOM4TE@ 未替换 → 127）。修法：build()
  里按依赖序 touch 时间链（m4/*.m4+configure.ac 最旧 < aclocal.m4 < configure <
  Makefile.in 最新）。**注意 os.utime 逐文件调用纳秒级递增**——必须按依赖顺序
  循环且时间值显式递增（`_touch_seq(t += 0.001)`），同刻乱序 touch 仍触发重建
- **test_package 的 cmake 启动**：PATH 上的 cmake 是 OHOS aarch64 ELF
  （NEEDED libc++_shared.so，在 /system/lib64），conan build env 替换式
  LD_LIBRARY_PATH 丢失系统路径 → rc=127。修法：Environment prepend
  /system/lib64:/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk
- **test_vlc 运行环境**：conan 的 cmake.test()（ctest）进程不含 conanrun 的
  LD_LIBRARY_PATH → test 二进制加载 libvlc.so.5 失败。self.run(env=list) 在
  OHOS loader 上不生效 → 用 `Environment().vars().apply()` 上下文 + VLC_PLUGIN_PATH
  指向包内 lib/vlc/plugins（libvlc_new 需插件树，否则报 stale plugins cache
  ——首次还需删 plugins.dat）

## 上游测试（N=22 实测）

vlc 3.0.23 的 test/Makefile.am 注册 `TESTS = $(check_PROGRAMS) check_POTFILES.sh`
（**不是**"无标准 make check"——比任务描述乐观，有完整 automake 套件）：
- 20 个无条件 check_PROGRAMS + test_modules_tls（ENABLE_SOUT 条件）+ check_POTFILES.sh = N 22
- 本机交叉构建 `make check` 实测：**PASS 17 / FAIL 4 / SKIP 1**
- 失败 4 项全部平台限制可定性：
  - test_src_input_stream / test_modules_keystore：硬编码 /tmp（OHOS 只读，E002）
  - test_libvlc_media：fd:// 目录枚举 subitem 超 alarm(10s)（HMDFS 慢，SIGALRM 142）
  - check_POTFILES.sh：校验 Qt 头存在性（--disable-qt 裁剪后必然缺失）
- SKIP 1：test_modules_tls（TLS 插件裁剪，上游 exit 77 语义）

## 依赖版本选型（制品仓实测可用）

ffmpeg/4.4.8（非任务描述的 2.8.9/4.4.6——仓内实际 4.4.8/5.1.10/6.1.6/7.1.5/8.0.3/8.1.2，
选 4.4.8 是 vlc 3.0.x 时代的稳定线）+ libmad/0.15.1b + dav1d/1.5.0 +
libogg/1.3.6（force 统一）+ libvorbis/1.3.7 + libtheora/1.2.0-alpha1 +
flac/1.5.0 + libopus/1.6.1 + libvpx/1.16.0 + x264/r3223 + x265/4.2 +
libdvdnav/7.0.0 + fribidi/1.0.16 + libass/0.17.5（字幕链 freetype/fontconfig/
harfbuzz 由 libass 传递）。

## 产物

- lib/libvlc.so.5.6.1 + lib/libvlccore.so.9.0.1（核心库）
- lib/vlc/plugins/ 下 25 类 283 个 *_plugin.so
- bin/vlc（命令行播放器入口，shell wrapper）
- include/vlc/ 完整公共头树

test_package：libvlc_get_version（3.0 前缀校验）+ libvlc_get_compiler +
libvlc_new(0,NULL)/libvlc_release 实例生命周期——5/5 PASS。
---

**编译结束**: 2026-09-25 12:21
**最终状态**: built
