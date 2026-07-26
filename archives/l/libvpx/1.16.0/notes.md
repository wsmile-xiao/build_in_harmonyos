# libvpx 1.16.0 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

WebM Project 的 VP8/VP9 编解码库，BSD-3-Clause。主要消费方是 FFmpeg 的
`--enable-libvpx`：FFmpeg 内建有 VP8/VP9 **解码**器，**编码**需外接 libvpx。

版本取 **1.16.0**（当前最新正式 tag）；上游 `v1.17.0-rc1` 是候选版，不采用。

## 关键适配

### 1. configure 是手写脚本，不是 autoconf —— 不能用 AutotoolsToolchain

libvpx 与 FFmpeg 同类：仓内**无 `configure.ac`**，`configure` 是手写 shell。它只认
`--prefix` / `--libdir` / `--target=` 及自有 `--enable/--disable` 开关，**连 `--includedir` 都没有**
（头文件固定装到 `<prefix>/include/vpx/`）；遇未知选项走 `build/make/configure.sh` 的
`die_unknown` 直接退出。`AutotoolsToolchain` 会传一串 autoconf 标准选项，必然当场失败。

故本配方 `generate()` 留空，全部参数在 `build()` 里按 libvpx 自己的选项名显式拼。

### 2. PATH 必须含 hnp bin —— 否则报「diff missing」（误导性报错）

`configure:195` 是 `if ! diff --version >/dev/null; then die "diff missing: Try installing
diffutils via your package manager."`，按**裸名**调 `diff`（`:199` 还有 `perl`）。
而 conan 的 `self.run` 走 `/bin/sh`，PATH 未必含 `/data/service/hnp/bin`。

**设备上 `diff` 其实是存在的**（`/data/service/hnp/bin/diff`，GNU diffutils 3.10，`--version` rc=0），
这条报错会把人引向「装 diffutils」的错误方向。正解是 `build()` 里把 hnp bin 前置进 PATH。

### 3. 工具链经环境变量覆盖

`build/make/configure.sh:745` 是 `CC=${CC:-${CROSS}gcc}`（AR/LD/AS/STRIP 同形）。
`--target=arm64-linux-gcc` 会让 CROSS 默认成 `aarch64-linux-gnu-`，去找不存在的
`aarch64-linux-gnu-gcc`。故 `build()` 里置 `CROSS=""` 并导出 CC/CXX/LD/AS/AR/NM/RANLIB/STRIP
为 hnp 全路径。

### 4. 裁剪

`--disable-examples --disable-tools --disable-docs --disable-install-docs --disable-unit-tests`
——单测另需下载数百 MB 测试数据，CI 不具备条件；示例/工具不进包。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native` **rc=0，31s**，包体积 2.1M。

- `lib/libvpx.so.12`，SONAME `libvpx.so.12`，DT_NEEDED 仅 `libc.so`
- `.codesign` 段存在
- `include/vpx/`、`lib/pkgconfig/vpx.pc` 齐全

### test_package（真实 VP8 编码，非仅版本查询）

`vpx_codec_enc_config_default` → `vpx_codec_enc_init` → `vpx_img_alloc` →
编 320x240 非均匀 I420 一帧 → NULL 冲刷 → 取 `VPX_CODEC_CX_FRAME_PKT` 累加字节数。

```
libvpx: version=v1.16.0  vp8 encoded 379 bytes from 320x240  OK
```

两个写测试时踩到、值得记下的 libvpx API 约束：

- **每次 `vpx_codec_encode` 之后必须立刻 drain 输出包**：`vpx_codec_get_cx_data` 的迭代器只覆盖
  本次调用产生的包，两次 encode 后才 drain 一次会丢掉前一次的输出。
- **VP8 默认 `g_lag_in_frames=25`**（alt-ref 前瞻），单帧测试会一直缓冲不出包，须置 0。

测试直接链 `-lvpx`（非 dlopen），CI 的 L1e 破坏性反向验证成立。

## 状态

built —— 真机 `conan create` + 真实 VP8 编码 test_package 全绿。
