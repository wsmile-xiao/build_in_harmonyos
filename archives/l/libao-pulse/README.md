# libao-pulse

libao（Xiph 跨平台音频输出库）的 **PulseAudio 变体**：交付 `libao.so.4` 与
PulseAudio 驱动插件 `lib/ao/plugins-4/libpulse.so`，不打包 OSS 等其它后端。

## Description

- `libao.so.4.1.1`：核心库，编译进 `null/wav/raw/au` 四个文件类驱动，
  其余后端通过 `dlopen` 插件提供（`include/ao/ao.h`、`lib/pkgconfig/ao.pc`）。
- `lib/ao/plugins-4/libpulse.so`：PulseAudio 输出插件，`DT_NEEDED` 为
  `libpulse-simple.so.0`、`libpulse.so.0`、`libc.so`。
- 库本体的归档目录是 `archives/l/libao`（当前只有文档与生成物补丁，无配方）；
  本目录是它可 `conan create` 的 PulseAudio 变体。

## Project URL
https://xiph.org/ao/ · https://gitlab.xiph.org/xiph/libao

## License
GPL-2.0-or-later

## HarmonyOS 适配说明

### 构建信息
- **上游版本**: 1.2.2（官方 git-archive `libao-1.2.2.tar.gz`，sha256 `df8a6d0e…e2bf4d`）
- **构建系统**: autotools（tarball 无 `configure`，`build()` 先 `autoreconf -fi`）
- **编译器**: clang（OHOS SDK）
- **依赖**: `pulseaudio/17.0.1`；构建期 `automake/1.18`、`libtool/2.5.4`
- **关键配置**: `--enable-pulse`、`--disable-{esd,arts,nas,alsa}`、`LIBS=`、
  `ac_cv_header_{sys,machine}_soundcard_h=no`

### 平台限制与处理

| 问题 | 根因 | 处理 |
|------|------|------|
| configure 探针 `cannot run C compiled programs` | `AutotoolsDeps` 把未签名的 `pulseaudio` `.so` 塞进 `LIBS`，探针程序加载失败 | 给 configure 传 `LIBS=` |
| `PULSE live output: no`、插件没被编译 | pkg-config 找不到 `libpulse-simple.pc`（老式 pkg.m4 分支不认预置变量） | `PKG_CONFIG_PATH` +`PKG_CONFIG_SYSROOT_DIR` 指向 pulseaudio 包 |
| `.pc` 里 `-I/include -L/lib` | 依赖包以 `prefix=/` 安装到 staging 目录 | 同上，`PKG_CONFIG_SYSROOT_DIR` 重挂前缀 |
| 插件装了但运行时找不到 | `AO_PLUGIN_PATH` 在 configure 时被写成 `/lib/ao/plugins-4`（只读系统目录） | patches/0001：允许同名环境变量覆盖（仅绝对路径；未设置/为空/相对路径保持上游行为） |
| 包里多出 `liboss.so` | OSS 由 `<sys/soundcard.h>` 存在与否决定，OHOS sysroot 里有该头文件 | autoconf cache 变量 `ac_cv_header_sys_soundcard_h=no` |
| `config.status` 临时目录 Permission denied | `umask 077` + HMDFS setgid | 改写生成出的 `configure` |
| 并行 make 失败 | HMDFS jobserver fifo (E074) | `make -j1` |

### 使用方式

```bash
# 链接包内的 libao
cc app.c $(pkg-config --cflags --libs ao) -o app
# 从 Conan 缓存直接使用插件（无需并入根文件系统；只接受绝对路径）
AO_PLUGIN_PATH=<pkg>/lib/ao/plugins-4 ./app
```

### 验证结果
- 真机 `conan create` 全绿：`CREATE_RC=0`，`test_package: 12 passed, 0 failed`，
  consumer `8/8 checks passed`（共 20 条断言；含 libao 真的 `dlopen` 插件并注册 pulse 驱动）。
- `configure` 摘要佐证变体正确：`PULSE live output: yes`、`OSS live output: no`。
- 已知限制：真机无 PulseAudio 服务端，`ao_open_live(pulse)` 返回 `NULL`
  （consumer 在该分支断言 pulse 驱动类型必须是 `AO_TYPE_LIVE`）；
  制品仓的 `pulseaudio/17.0.1` 缺 `.codesign`，真机运行需平台已签名的
  `libpulse.so.0`/`libpulse-simple.so.0`（详见 `1.2.2/notes.md`）。
