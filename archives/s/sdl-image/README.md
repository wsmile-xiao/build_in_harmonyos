# sdl-image

## 简介

sdl-image 是 SDL **1.2** 的图像加载扩展库（上游 `SDL_image`），提供 `IMG_Load` 系列 API，
支持 PNG、JPEG、TIFF、WebP、BMP、GIF、PCX、TGA、XCF、LBM、PNM 等格式。

SDL 1.2 本体由依赖 `sdl12-compat`（1.2 API 兼容实现）提供，本包依赖其头文件与 `libSDL-1.2`。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.2.12 | published | 2026-09-13 |

## 依赖

- **sdl12-compat** 1.2.68（必需，提供 SDL 1.2 API）
- **libpng** 1.6.58
- **libjpeg-turbo** 3.2.0
- **libtiff** 4.7.2
- **libwebp** 1.6.0

## 构建说明

- 构建系统：autotools（上游 2012 年版本，`config.sub` 不识别 `aarch64`/`-linux-ohos`，
  由 `patches/0001-config.sub.patch` 补齐；配方同时显式传入
  `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` 强制交叉模式）。
- 产物：静态库 `libSDL_image.a` 与头文件 `include/SDL/SDL_image.h`（库类默认静态，避免与系统同名库冲突）。
- 上游无测试套件（仅 `noinst_PROGRAMS = showimage` 示例），已登记 `ci/config/no_official_test.txt`，
  验证由 `test_package/` 消费者测试承担（8 项断言，覆盖版本一致性、编解码器初始化、格式嗅探、
  PNG/BMP 解码与错误路径）。

## 使用

```cmake
find_package(SDL_image REQUIRED CONFIG)
target_link_libraries(app PRIVATE SDL_image::SDL_image SDL::SDL)
```

```c
#include <SDL/SDL.h>
#include <SDL/SDL_image.h>

IMG_Init(IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_TIF | IMG_INIT_WEBP);
SDL_Surface *img = IMG_Load("picture.png");
```

> 注意：已发布的 `sdl12-compat/1.2.68` 未导出 include 目录（其头文件位于包内 `include/SDL/`），
> 消费者若遇到 `SDL.h` 找不到，可用 `dependencies["sdl12-compat"].package_folder` 自行定位。
