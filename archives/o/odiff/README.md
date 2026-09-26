# odiff

**ODiff** 是一个极快的（单线程）像素级图像对比命令行工具，用于比较两张图片的视觉差异，以毫秒级完成截图、照片、AI 生成图等的对比。最初用 OCaml 编写，现为 Zig + SIMD（SSE2/AVX2/AVX512/NEON）实现。

## 功能概述
- 支持 `.png` / `.jpeg` / `.jpg` / `.webp` / `.tiff` / `.bmp` 格式对比；
- 跨格式对比（如 `.jpg` vs `.png`）；
- 反锯齿（anti-aliasing）检测、忽略区域、YIQ NTSC 色差算法、diff 输出、diff 行列输出；
- SIMD 优化（SSE2/AVX2/AVX512/NEON）、`--enable-asm` 汇编路径、可选 server 模式。

## OHOS 适配
- odiff 是 Zig 项目（`minimum_zig_version=0.16.0`），用 `zig/0.16.0.1` 工具构建；
  SDK 的 OHOS aarch64 无问题，产物需签名后才能在 HarmonyOS 执行。
- 依赖树（imgz 及 spng/jpeg/tiff/webp/zlib/zstd）整棵 vendoring 到 `deps/`，并把各
  `build.zig.zon` 改写为 `.path` 本地依赖，`zig build` 全程离线。
- OHOS 上需清掉 CC/CXX/CFLAGS 等环境变量，让 Zig 使用自带 musl 头。
- libtiff 使用官方稳定版 4.7.2 替代 imgz 钉的不可达 gitlab commit（详见 notes.md）。

## 依赖关系
- 构建依赖：`zig/0.16.0.1`
- 上游内嵌 C 依赖：libspng、libjpeg-turbo、libtiff、libwebp、zlib、zstd（经 imgz vendoring）

## 参考资料
- 官网/源码: https://github.com/dmtrKovalenko/odiff
- 上游版本: v4.5.0
