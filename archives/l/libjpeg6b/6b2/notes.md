# libjpeg6b 6b2 适配笔记

## 基本信息
- 上游：Debian 源码包 libjpeg6b 6b2（IJG jpeg-6b 谱系的 Debian 维护版）
  https://deb.debian.org/debian/pool/main/libj/libjpeg6b/libjpeg6b_6b2.orig.tar.gz
- 版本身份：JVERSION "6b 27-Mar-1998"，JPEG_LIB_VERSION = 62，autoconf 包名 libjpeg 6.2.1
- 谱系：jpeg-6b (1998) -> 6b1 (2010, 换 libjpeg8 的 autoconf/libtool 构建系统) ->
  6b2 (2013, 仅改 jdmarker.c，加入 CVE-2013-6629/6630 信息泄露修复)
- license：IJG（无独立 LICENSE 文件，正文在 README 的 LEGAL ISSUES 段，
  copyright (C) 1991-1998 Thomas G. Lane）；package() 把 README/README.6b2 拷入 licenses/
- 构建系统：autotools（归档自带 autoconf 2.65 生成的 configure + automake 1.11.1 生成的
  Makefile.in，无需 autoreconf）
- 依赖：无（纯 C89，仅 libc；内存后端默认 jmemnobs，malloc/free，musl 友好）
- 无 SIMD/asm（jmemdosa.asm 仅 DOS 用），无 nasm 依赖

## 配方要点
- `--enable-static --disable-shared`：6b2 的 libtool `-version-info 62` 会产出 SONAME
  `libjpeg.so.62`，与 libjpeg-turbo 的 classic ABI 同名（R26）。仅产出 `libjpeg.a`，
  避免动态库落到系统库搜索路径造成覆盖。
- 包名 `libjpeg6b` 与已有 `libjpeg`（IJG 10）是不同 conan 包、不同谱系；但头文件同名
  （jpeglib.h/jconfig.h/jerror.h/jmorecfg.h），消费方二选一，不可同时链接。
- `build()` 在 `make` 之后执行 `make check`，直接复用上游 `Makefile.am` 的 `check-local`。
- **make 全程 `-j1`（build/check/install）**，两个原因：
  1. HMDFS 不支持 make jobserver 的 mkfifo（并行时 `make: jobserver mkfifo: Operation not permitted`）；
  2. 6b2 的 install 规则会并发创建 `$(includedir)`：`install-data-local`（Makefile.in:1065，
     装 jconfig.h，用 `mkinstalldirs` = `install-sh -d`）与 `install-includeHEADERS`
     （Makefile.in:857，用 `MKDIR_P`，autoconf 2.65 在本设备探测失败回退为
     `install-sh -c -d`）都各自先建目录，`make install -j20` 下两者竞态，
     install-sh 对竞态 EEXIST 直接 `mkdir: ... File exists` 报错，install 崩溃
     （round-01 CI 实证）。串行执行时 install-sh 先 `test -d` 再建目录，完全正常。
     jpeg-10（autoconf 2.69+，MKDIR_P=真 mkdir -p）不受此影响。
- 产物：`libjpeg.a`，头文件 4 个，可执行文件 `cjpeg`/`djpeg`/`jpegtran`/`rdjpgcom`/`wrjpgcom`
  （因此软件级补充 `commands.json`，R38）。

## 补丁

### 0001-config.guess.patch + 0002-config.sub.patch（E007 平台识别，双补丁）
与 jpeg-10 不同，6b2 的 config.guess 与 config.sub 都是 2009-11-20 版，两枚都过旧：
- config.guess 的 case 分派没有 HarmonyOS 分支，configure 报 `cannot guess build type`。
  补丁新增 `*:HarmonyOS:*:*)` 分支，按 `uname -m` 归一化后输出
  `aarch64-unknown-linux-ohos`（实机验证：HarmonyOS HongMeng Kernel 1.12.0 上输出正确）。
- config.sub 两处缺口：(1) 文件头的 maybe_os KERNEL-OS 组合列表不认识 `linux-ohos`，
  导致 `aarch64-unknown-linux-ohos` 被错误切成 basic_machine=`aarch64-unknown-linux` +
  os=`-ohos`，随后 CPU 匹配直接报 `machine not recognized`；(2) CPU 列表不认识 `aarch64`。
  补丁仿照 2024-05-27 版 config.sub 的做法：maybe_os 列表加 `linux-ohos*`、CPU 列表加
  `aarch64`，并在 os case 中在通用 `-linux*` 改写（会把 os 变成 `-linux-gnu-ohos`）之前
  新增 `-linux-ohos*)` 保形分支。补丁后 `config.sub aarch64-unknown-linux-ohos`
  输出与仓内 jpeg-10 自带的 2024 版 config.sub 完全一致。
- jpeg-10 的 0001 补丁思路可参考，但本包 config.guess 的 case 行使用 `${...}` 花括号
  变量、且需要连 config.sub 一起补，上下文完全不同，必须重做。

### 0003-configure-umask.patch（E011 HMDFS umask）
`configure`（autoconf 2.65 生成，13700/13705 行）用 `umask 077 && mktemp -d` 创建临时目录，
HMDFS 上 700 权限目录内无法再创建文件，`config.status` 报
`can't create ./confXXX/subs1.awk: Permission denied`。补丁把两处 `umask 077` 改为 `umask 022`，
与 jpeg-10 的 0002 同法（行号不同，hunk 重做）。

## 测试

### 上游测试（已集成进 build()）
`make check` -> `check-local`（Makefile.am 末尾）：`djpeg` 解码 `testorig.jpg`
（ppm + bmp 256 色）、`cjpeg` 编码 `testimg.ppm`（基线 + 渐进）、`jpegtran` 转换
`testprog.jpg`，随后 6 条 `cmp` 与参考图像逐字节比对，任一不一致即 make 失败。
测试数据 6 个文件随归档分发（EXTRA_DIST TESTFILES），无需网络。

### test_package（消费者视角）
`test.c` 用 `jpeg_stdio_dest` 把 64x48 RGB 渐变图以质量 90 编码进当前目录临时文件，
校验文件大小与 SOI 标记（0xFFD8）；再用 `jpeg_stdio_src` + `jpeg_read_header` +
`jpeg_read_scanlines` 解回，校验尺寸与分量数，并对每行全部像素与原图逐字节比对
（有损编码，阈值 16），结束后删除临时文件。特意不使用 `jpeg_mem_src/jpeg_mem_dest`
（jpeg-8 才有这两个 API），也特意不 include `stdbool.h`（jmorecfg.h 里
`typedef int boolean`，与 C99 bool 冲突）。

## 状态
- status: built（配方验证通过，CI 在鸿蒙 worker 上 conan create 全门禁通过）
