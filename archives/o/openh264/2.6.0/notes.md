# openh264 2.6.0 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

Cisco OpenH264，H.264 编解码库，BSD-2-Clause。主要消费方是 FFmpeg 的 `--enable-libopenh264`。

**选它而不是 x264 的原因是许可**：x264/x265 在 FFmpeg 的 `EXTERNAL_LIBRARY_GPL_LIST` 里，
启用会触发 `die_license_disabled gpl`、强制 `--enable-gpl`，使整个 FFmpeg 包从 LGPL-2.1 变成 GPL。
openh264 是 BSD，可与 LGPL 的 FFmpeg 组合而不传染许可。

## 关键适配（meson，两个坑）

### 1. `FIXME: Unhandled system harmonyos`

conan 的 `MesonToolchain` 把 `os=OHOS` 映射成 meson 的 `system = 'harmonyos'`，而 openh264 的
`meson.build:60` 是

```meson
if ['linux', 'android', 'ios', 'darwin'].contains(system)
```

白名单不含它 → 落到 `meson.build:143` 的 `else` 报 `error('FIXME: Unhandled system @0@')` 而中止。

`build()` 里把 `harmonyos` 补进该白名单。OHOS 与 linux 同为 ELF + POSIX + clang 工具链，
该分支内的 asm 格式选择与链接处理完全适用（属实质适配，非空壳 stub）。
补丁带防御：若上游改动使新旧形态都匹配不上，抛 `ConanInvalidConfiguration` 而不是静默跳过。

### 2. meson 找不到归档器 `llvm-ar`

conan 的 `MesonToolchain` 不把 `tools.build:compiler_executables` 里的 ar/ranlib 写进 native file，
meson 便按**裸名**探 `llvm-ar`；而工具链在 `/data/service/hnp/bin`、PATH 上没有时 configure 直接失败。
`generate()` 里把 ar/ranlib **全路径**注入 `conan_meson_native.ini`（从 c 编译器同目录推导），不污染 PATH。

### 3. `tests=disabled`

上游 test 子目录依赖 gtest wrap 子项目，而本配方设了 `wrap_mode=nodownload`（禁止 meson 偷偷下依赖）。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native` **rc=0，18s**，包体积 1.4M。

- `lib/libopenh264.so.7`，SONAME `libopenh264.so.7`
- DT_NEEDED 含 `libc++_shared.so`（openh264 是 C++ 库，属预期）与 `libc.so`
- `.codesign` 段存在
- `include/wels/`、`lib/pkgconfig/openh264.pc` 齐全

### test_package（真实 H.264 编码，非仅版本查询）

用 C++（`test.cpp`）走其 C++ 接口——openh264 是 C++ 库，C 程序链接它需额外带 C++ 运行时：
`WelsCreateSVCEncoder` → `Initialize(320x240)` → `EncodeFrame`(非均匀 I420) → 遍历 NAL 累加长度。

```
openh264: version=2.6.0  encoded 360 bytes (2 layer(s)) from 320x240  OK
```

断言：`EncodeFrame` 返回 `cmResultSuccess`、帧类型非 `videoFrameTypeSkip`、NAL 总字节数 > 0。
测试直接链 `-lopenh264`（非 dlopen），CI 的 L1e 破坏性反向验证成立。

## 状态

built —— 真机 `conan create` + 真实 H.264 编码 test_package 全绿。
