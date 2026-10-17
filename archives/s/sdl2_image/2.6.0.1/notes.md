# SDL2_image 2.6.0.1 适配笔记

## 背景

AssaultCube（基于 Cube1 的 FPS）适配 OpenHarmony PC（aarch64）时暴露两个独立平台问题，需要 SDL2_image 一个小版本：

1. **SDL2 无法在 OHOS 上创建 GL 上下文**：EGL 默认路径硬性要求 `eglQueryDevicesEXT`，OHOS libEGL 无此扩展。`sdl2/2.30.10.1` 带 0006 EGL 回退补丁解决。
2. **SDL2_image 的 stb 后端无法解码灰度+alpha PNG**：AssaultCube 字体是灰度+alpha（color type 4）PNG，stb 后端映射成未知像素格式。改用 **libpng 后端**可原生解码。

因此创建新小版本 `sdl2_image/2.6.0.1`，合并两条需求到同一依赖链。

## 编译环境

- 构建系统：CMake（Conan 2.29.1 驱动，`conan create`）
- 编译器：clang 15.0.4（aarch64-unknown-linux-ohos）
- 目标平台：OHOS aarch64（`os.version=6.0`，`arch=armv8`，`libc++17`，Release）
- 构建 profile：`ci/conan/profiles/ohos-aarch64`（host=build）
- 状态：built

## 构建步骤

```bash
python3 -m conans.conan create archives/s/SDL2_image/2.6.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方在 `archives/s/SDL2_image/2.6.0.1/`（`conanfile.py` / `conandata.yml` / `test_package/`）。

## OHOS 适配要点（三类通用问题）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake try-compile 失败 | OHOS 容器 `/bin/sh` 为 execute-only，GNU make 对 `/bin/sh` 做 `stat` 报 Permission denied（E009/E011） | `CMAKE_C_COMPILER_WORKS=TRUE` 跳过试编译 + 改用 Ninja generator（directly exec `/bin/sh`，绕过 make 的 stat 检查） |
| 2 | SDL_image 找不到 libpng/libwebp 库 | HMDFS 不跟踪符号链接（E050/E073），conan 缓存内 `.so` 符号链接不可访问，conan CMakeDeps 的 `find_library` 失败 | 在 generate() 内做**实体镜像**：把包内实体 `.so` 复制到可写镜像目录并生成无版本实体别名，再重定向依赖 `cpp_info.libdirs/includedirs` 指向镜像；对 webp 的 Findwebp 模块注入 `webp_LIBRARY`/`webp_INCLUDE_PATH`；运行时通过 `LD_LIBRARY_PATH` 指向镜像 |
| 3 | libtiff 链不可用 | OHOS 无 libtiff 二进制且 zstd 依赖链复杂 | `SDL2IMAGE_TIF=OFF` 裁剪 |
| 4 | 字体 PNG 解码损坏 | stb 后端无法解码灰度+alpha PNG | `SDL2IMAGE_BACKEND_STB=OFF` + `SDL2IMAGE_PNG=ON`，用 libpng 后端 |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| sdl2 | 2.30.10.1 | SDL2 底座（含 0006 EGL 回退补丁） |
| libpng | 1.6.58 | PNG 解码（灰度+alpha） |
| libjpeg-turbo | 3.2.0 | JPEG 纹理 |
| libwebp | 1.6.0 | WebP 解码头文件 |

（以上均为 main 上已有可用配方，无需自适配。）

## 源码修改

无（源码与 2.6.0 相同，仅依赖/选项不同）。

## 验证结果

- 编译状态：通过
- 上游测试：`ctest` 单测 `testimage` → `1/1 Passed (100%)`
- test_package 消费者测试：`test_sdl2_image` 通过 —— 断言 `IMG_Init(PNG|JPG|WEBP)` 三格式可用，并成功解码 **灰度+alpha PNG**（color type 4）
- 总通过率：`100%`

## 交付物

- 配方：`archives/s/SDL2_image/2.6.0.1/`（conanfile.py、conandata.yml、test_package/）

## 注意事项

- 依赖 shared 库（libpng/libwebp）的符号链接在 OHOS 受限，配方内的实体镜像处理属于适配必需；正式 CI 若能访问符号链接则可省略（镜像逻辑幂等、无副作用）。
- 测试二进制为 OHOS ELF，需 `binary-sign-tool` 签名后才能运行。

---

**编译结束**：2026-09-03
**最终状态**：built
**质量门禁**：G1-G4 PASS ✅（conan create + test_package 全部通过）
