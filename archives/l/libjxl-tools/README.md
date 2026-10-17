# libjxl-tools

JPEG XL reference implementation **command-line tools**（`cjxl` 编码器、`djxl` 解码器、`jxlinfo` 容器信息查看器），为 HarmonyOS PC (arm64 / OHOS) 适配的 Conan 2.x 配方。

## Description

libjxl-tools 从 libjxl 源码树构建用户态命令行工具：

- `cjxl` — JPEG XL 编码器（输入 PPM/PFM/PNG 等，输出 `.jxl`）
- `djxl` — JPEG XL 解码器（输出 PPM/PFM/PNG 等）
- `jxlinfo` — 打印 `.jxl` 容器的编解码器 / 元数据 / 盒子信息

本适配**必需** PNG 依赖（libjxl extras 无条件启用 APNG 编解码），由 `libpng/1.6.58`
（传递 `zlib/1.3.1.1`）提供，并随包分发 `libpng16.so` 与合成的 `libz.so` 使工具自包含。
其余可选编解码依赖（JPEG/GIF/WebP/OpenEXR/jpegli）关闭；PPM/PFM/PNG ⇄ JXL 完整编解码链路可用。

## Homepage

https://github.com/libjxl/libjxl

## Build System

CMake

## Dependencies

- **Required**: brotli/1.2.0（动态）、highway/1.3.0.2（静态）、libpng/1.6.58（动态，传递 zlib/1.3.1.1）
- **Bundled**: skcms（内置色彩管理，source() 阶段下载上游锁定 commit）
- **Shipped in package lib/**: `libbrotli*.so*`、`libpng16.so*`、`libz.so`（由静态 `libz.a` 合成）

## Tools Provided

- `cjxl`: JPEG XL encoder
- `djxl`: JPEG XL decoder
- `jxlinfo`: JPEG XL container info
