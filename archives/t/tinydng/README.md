# tinydng

Tiny but portable DNG (Digital Negative) image loader/writer — header-only C++11 单头文件库。

- 官方仓库：https://github.com/syoyo/tinydng
- 许可证：MIT（附带 miniz/stb 系公共域名或 MIT 许可组件，随源码分发）
- 版本：0.1.0（标签 `v0.1.0`）
- 目录结构：`archives/t/tinydng/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
- 适配形态：`package_type = "header-library"`，打包 `tiny_dng_loader.h`、`tiny_dng_writer.h`、
  `stb_image.h`、`miniz.h`、`miniz.c` 到 `include/`；无外部依赖
- CMake 目标名：`tinydng::tinydng`（`find_package(tinydng CONFIG REQUIRED)`）
