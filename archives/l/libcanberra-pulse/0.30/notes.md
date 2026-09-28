# libcanberra-pulse 0.30 适配笔记

## 1. 这个包是什么

libcanberra 是 XDG Sound Theme/Name 事件声音库（公共 API `canberra.h` /
`libcanberra.so.0`，真实文件 `libcanberra.so.0.2.5`，libtool `-version-info 2:5:2`）。

已归档的 `archives/l/libcanberra/0.30` 是**自包含变体**：`--with-builtin=null`
把 null 驱动编进库里（无音频设备即可冒烟），真实后端全部关闭。
本任务（13083）做的是 **PulseAudio 变体**：`--with-builtin=pulse` 把 `pulse.c`
直接编进 `libcanberra.so`，产出的 `libcanberra.so.0` 与库本体同名同 SONAME，
但多一条硬运行时依赖 `libpulse.so.0`，从而真正与 PulseAudio 服务端通信。

两者共用同一份上游源码与大部分补丁；本目录可 `conan create`。

## 2. 配方结构

- 源码：官方 `https://0pointer.de/lennart/projects/libcanberra/libcanberra-0.30.tar.xz`，
  sha256 `c2b671e67e0c288a69fc33dc1b6f1b534d07882c2aceed37004bf48c601afa72`
  （`conandata.yml` 校验）。
- 5 个补丁，与 `archives/l/libcanberra/0.30` 的对应关系如下（仅重新编号）：

  | 本包 | 库本体 | 作用 |
  |------|--------|------|
  | 0001-vorbis-optional | 0001 | read-vorbis.c 整份包进 `#if HAVE_VORBIS` |
  | 0002-vorbis-read-sound-file-guards | 0002 | read-sound-file.c 的 vorbis 回退分支加守卫 |
  | 0003-config.guess-harmonyos | 0004 | config.guess 认 HarmonyOS（`cannot guess build type`） |
  | 0004-config.sub-ohos | 0005 | config.sub 接受 `linux-ohos` |
  | 0005-configure-ltdl | 0006 | 中和 configure 的 libltdl 硬门禁 |

  库本体的 `0003-null-driver-playing.patch` **本包不需要**：那是 null.c 漏实现
  `driver_playing()` 才要补的 stub（common.c 无条件调用它），而 `pulse.c`
  自己实现了该函数。
- 只构建/安装 `src` 子目录（顶层 `SUBDIRS = src gtkdoc doc`）；`libcanberra.pc`
  是顶层 AC_CONFIG_FILES 产物，由配方自行复制进 `lib/pkgconfig/` 并把 `prefix=`
  改写为 `${pcfiledir}/../..`，同时删除 `libcanberra.la`。
- configure 在 `/system/bin/sh` 下以 `--host=aarch64-linux-ohos --srcdir=...`
  交叉模式运行（只给 `--host`）；生成的 `configure` 里恰好 2 处 `umask 077`
  改写为 `022`（HMDFS 强制 setgid，`077` 下 `mktemp -d` 得到的目录属主自己也
  进不去）；`make` 固定 `-j1`（HMDFS jobserver fifo 返回 EPERM）。

## 3. 关键适配点

### 3.1 vorbis 强制依赖绕过（继承库本体）
上游 `configure.ac:586` 的 `PKG_CHECK_MODULES(VORBIS, [vorbisfile])` **无条件**，
没有 `--disable-*` 开关，制品仓又没有 vorbis/libogg。配方喂
`VORBIS_CFLAGS=-DHAVE_VORBIS=0` 与 `VORBIS_LIBS=' '`（注意是空格）——
两者都非空时内置的老版 pkg.m4 才走 env 分支、永不调用 pkg-config。
WAV（read-wav.c）解码保留。

### 3.2 pulse 依赖解析：老式 pkg.m4 + staging 前缀
`configure.ac` 用 `PKG_CHECK_MODULES(PULSE, [libpulse >= 0.9.11])` 解析驱动。
制品仓 `pulseaudio/17.0.1` 带 `lib/pkgconfig/libpulse.pc`，但该 `.pc` 记录的是
`prefix=/`（依赖以 staging 前缀安装），只设 `PKG_CONFIG_PATH` 会得到
`-I/include -L/lib`；再补 `PKG_CONFIG_SYSROOT_DIR=<pulseaudio.package_folder>`
让 pkg-config 把 `-I`/`-L` 重挂回包目录，于是 configure 报

    checking for PULSE... yes

（与 libao-pulse 同源的两个坑：本镜像 autoconf-2.72 展开的是老式 pkg.m4 分支，
预置 `PULSE_CFLAGS`/`PULSE_LIBS` 不生效，必须让 `pkg-config --exists` 真的成功。）

### 3.3 `LIBS=`：未签名依赖库会让所有 configure 探针失败
`AutotoolsDeps` 把每个依赖库都塞进 `LIBS`，而 configure 的**每个**探针程序都会
链接 `LIBS`。制品仓 `pulseaudio/17.0.1` 的二进制缺 `.codesign` 段，OHOS 加载器
拒绝映射这类对象，最基础的「C 编译器可用吗」探针直接：

    configure: error: cannot run C compiled programs
    ... Error loading shared library libpulse.so.0

处理：OHOS 分支给 configure 传 `LIBS=`（autoconf 的 precious variable，命令行
赋值合法且会 export），探针不再链接任何外部库；驱动自身的链接由
`src/Makefile.am` 的 `$(PULSE_LIBS)` + `AutotoolsDeps` 提供的 `-L<abs libdir>` 完成。

### 3.4 `--with-builtin=pulse` 与 libltdl 硬门禁
`--with-builtin=pulse` 关掉 `BUILTIN_DSO`（不编 dso.c/driver-order.c、不链
`$(LIBLTDL)`），同时把 `HAVE_ALSA/HAVE_OSS/HAVE_GSTREAMER/HAVE_NULL` 强制为 0，
所以不需要插件目录、也不需要 libltdl。但 configure 在 ltdl 探测之后仍**无条件**
`if test "x$LIBLTDL" = "x"; then AC_MSG_ERROR(Unable to find libltdl.)`——
`patches/0005` 中和该门禁（只影响这个硬错，不改探测逻辑）。

### 3.5 产物确实编入了 pulse 后端
`--with-builtin=pulse` 的产物里没有可 dlopen 的插件模块，也没有「当前编入哪个
驱动」的公开查询接口。本配方用两条可观测证据证明：

- **ELF 层**：`libcanberra.so.0` 的 `DT_NEEDED` = `libpulse.so.0` + `libc.so`
  （库本体的 null 变体只有 `libc.so`），`test_package` 在运行时校验这一点；
- **行为层**：每个后端在 `driver_open()` 开头都有驱动名守卫，例如 pulse.c
  `ca_return_val_if_fail(!c->driver || ca_streq(c->driver, "pulse"), CA_ERROR_NODRIVER)`。
  于是 `ca_context_open` 对 `"pulse"` 能过守卫（无服务端时返回
  `CA_ERROR_NOTAVAILABLE(-12)`），对 `"null"`/`"alsa"`/`"no-such-backend"`
  一律 `CA_ERROR_NODRIVER(-5)`；而 `archives/l/libcanberra/0.30` 恰好相反
  （`"null"` 返回 `CA_SUCCESS`）。该判定发生在任何服务端交互之前，
  无需声卡、无需服务端。

## 4. 真机验证（conan create 全绿）

    checking for PULSE... yes
    libcanberra-pulse/0.30: Package '3ede511660589a725610954353afc1822d4019b6' created
    libcanberra.so.0 pins DT_NEEDED libpulse.so.0 (pulse backend compiled in)
    api_surface: 61 checks, 0 failed, 19 symbols relocated
    INFO: ca_context_open(pulse) -> -12 (Not available)
    pulse_contract: 74 checks, 0 failed
    CREATE_RC=0

两个 consumer 共 **135 条断言**全过。安装布局：
`include/canberra.h`、`lib/libcanberra.so.0.2.5`（+`libcanberra.so.0`/`libcanberra.so` 链接）、
`lib/pkgconfig/libcanberra.pc`、`licenses/LGPL`。

## 5. 已知限制

- 真机没有 PulseAudio 服务端：`ca_context_open("pulse")` 返回
  `CA_ERROR_NOTAVAILABLE(-12)`，`ca_context_play_full()` 也不会成功
  （consumer 把这一点断言为「无服务端时不应成功」，属预期，见
  `test_package/pulse_contract.c`）。
- 制品仓 `pulseaudio/17.0.1` 缺 `.codesign`，OHOS 加载器不会映射它，因此
  `libcanberra.so.0`（`DT_NEEDED libpulse.so.0`）在纯 `conanrun` 环境里无法完成
  重定位（`pa_stream_unref: symbol not found`）。`test_package` 先跑一次并记录
  该现状（不判失败），再用 `LD_LIBRARY_PATH` 指向平台已签名客户端库
  （`/system/lib64/libpulseaudio.z.so` 软链成 `libpulse.so.0`）跑正式断言。
  真机运行同样需要这一步软链。这是依赖包的现状，不是本包的补丁能解决的。
- `gtkdoc/`、`doc/` 不构建（`--disable-gtk-doc`）；`bin/` 目录由 automake 的
  install 流程创建但为空。
