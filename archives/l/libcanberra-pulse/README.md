# libcanberra-pulse

libcanberra（XDG Sound Theme/Name 事件声音库）的 **PulseAudio 变体**：把 pulse 驱动
直接编进 `libcanberra.so`，交付一个真正与 PulseAudio 服务端通信的 `libcanberra.so.0`。

## Description

- `libcanberra.so.0.2.5`（`libcanberra.so.0` / `libcanberra.so`）：核心库，
  `--with-builtin=pulse` 把脉冲驱动编入其中，`DT_NEEDED` = `libpulse.so.0` + `libc.so`。
- `include/canberra.h`、`lib/pkgconfig/libcanberra.pc`（`prefix` 改写为
  `${pcfiledir}/../..`，可随包直接使用）。
- 库本体的自包含（null 驱动）归档是 `archives/l/libcanberra/0.30`；
  本目录是它可 `conan create` 的 PulseAudio 变体。

## Project URL
http://0pointer.de/lennart/projects/libcanberra/

## License
LGPL-2.1-or-later

## HarmonyOS 适配说明

### 构建信息
- **上游版本**: 0.30（官方 `libcanberra-0.30.tar.xz`，sha256 `c2b671e6…fa72`）
- **构建系统**: autotools（交叉模式 `--host=aarch64-linux-ohos --srcdir=...`，在 `/system/bin/sh` 下运行）
- **编译器**: clang（OHOS SDK）
- **依赖**: `pulseaudio/17.0.1`
- **关键配置**: `--with-builtin=pulse --enable-pulse --disable-null`
  `--disable-{alsa,oss,gstreamer,udev,gtk,gtk3,tdb,lynx,gtk-doc}`，`LIBS=`，
  `VORBIS_CFLAGS=-DHAVE_VORBIS=0`、`VORBIS_LIBS=' '`，
  `PKG_CONFIG_PATH`+`PKG_CONFIG_SYSROOT_DIR` 指向 pulseaudio 包

### 平台限制与处理

| 问题 | 根因 | 处理 |
|------|------|------|
| `vorbisfile` 缺失导致 configure 中止 | 上游 `PKG_CHECK_MODULES(VORBIS, vorbisfile)` 无条件、无开关 | `VORBIS_CFLAGS=-DHAVE_VORBIS=0` + `VORBIS_LIBS=' '`（两者非空即绕过 pkg-config），patches/0001/0002 守卫解码器 |
| configure 探针 `cannot run C compiled programs` | `AutotoolsDeps` 把无 `.codesign` 的 pulseaudio 库塞进 `LIBS`，探针加载失败 | 给 configure 传 `LIBS=` |
| `PKG_CHECK_MODULES(PULSE, ...)` 找不到依赖 | `.pc` 记录 `prefix=/`（staging 前缀），且老式 pkg.m4 不认预置变量 | `PKG_CONFIG_PATH` + `PKG_CONFIG_SYSROOT_DIR` 指向 pulseaudio 包 |
| configure 报 `Unable to find libltdl` | ltdl 探测后的无条件硬错，但 `--with-builtin=pulse` 已关 `BUILTIN_DSO`、根本不链 `$(LIBLTDL)` | patches/0005 中和该门禁 |
| `cannot guess build type` / `system ohos not recognized` | 2009 年的 `config.guess`/`config.sub` 不认 HarmonyOS | patches/0003 / 0004 |
| `config.status` 临时目录 Permission denied | `umask 077` + HMDFS setgid | 改写生成出的 `configure`（恰好 2 处） |
| 并行 make 失败 | HMDFS jobserver fifo (EPERM) | `make -j1` |
| 装了库但真机无法运行 | 制品仓 `pulseaudio/17.0.1` 缺 `.codesign`，加载器拒绝映射 `libpulse.so.0` | 平台已签名客户端库软链为 `libpulse.so.0`（运行期要求，见下） |

### 使用方式

```bash
# 链接包内的 libcanberra（PulseAudio 后端）
cc app.c $(pkg-config --cflags --libs libcanberra) -o app

# 真机运行时：制品仓的 pulseaudio 未签名，需先把平台已签名客户端库软链成 SONAME
ln -sf /system/lib64/libpulseaudio.z.so  <dir>/libpulse.so.0
LD_LIBRARY_PATH=<dir> ./app
```

### 验证结果
- 真机 `conan create` 全绿：`CREATE_RC=0`，configure 摘要 `checking for PULSE... yes`，
  `Package '3ede511660589a725610954353afc1822d4019b6' created`。
- `test_package` 两个 consumer **135 条断言全过**：
  `api_surface: 61 checks, 0 failed, 19 symbols relocated`、
  `pulse_contract: 74 checks, 0 failed`。
- 后端判定：`libcanberra.so.0` 的 `DT_NEEDED` 含 `libpulse.so.0`；
  `ca_context_open("pulse")` → `-12 (Not available)`（过驱动名守卫、无服务端），
  `"null"`/`"alsa"`/`"no-such-backend"` → `CA_ERROR_NODRIVER`。
- 已知限制：真机无 PulseAudio 服务端，`ca_context_play_full()` 不会成功；
  制品仓 `pulseaudio/17.0.1` 缺 `.codesign`（详见 `0.30/notes.md`）。
