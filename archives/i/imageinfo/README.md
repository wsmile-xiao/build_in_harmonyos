# imageinfo

[imageinfo](https://github.com/xiaozhuai/imageinfo) — Header-only C++17 library to get image info and size (width / height) from an image, and a CLI tool `imageinfo`.

- 版本：2.0.0（上游 tag `v2.0.0`，commit `126b391916169dc27bcdc3e555c7f73a95403bc2`）
- 类型：header-only 库 + CLI 工具（type: tool，见 commands.json）
- 支持格式：avif / heic / bmp / cur / ico / dds / gif / hdr / icns / j2k / jp2 / jpg / png / psd / svg / tga / tiff / webp 等
- 许可证：MIT

## 使用

```bash
conan install imageinfo/2.0.0
```

CMake 消费者通过 `find_package(imageinfo)` + 链接 `imageinfo::imageinfo` 使用；CLI 工具为 `imageinfo <file>`。