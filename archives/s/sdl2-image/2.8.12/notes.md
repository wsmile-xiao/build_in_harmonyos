# sdl2-image 2.8.12 适配笔记

## 编译环境
- 构建系统: CMake（上游同时提供 autotools；CMake 路径绕开 autotools heredoc 权限问题 E009/E011）
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

1. **依赖**：sdl2/2.30.10、libtiff/4.7.2、libwebp/1.6.0 均已在 ohpcd 制品仓发布，`conan download --only-recipe` 全部解析到。

2. **CMake 配置**（OHOS 适配）：
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DBUILD_SHARED_LIBS=OFF -DSDL2IMAGE_INSTALL=ON -DSDL2IMAGE_DEPS_SHARED=OFF \
     -DSDL2IMAGE_VENDORED=OFF -DSDL2IMAGE_SAMPLES=OFF -DSDL2IMAGE_TESTS=ON \
     -DSDL2IMAGE_TIF=ON -DSDL2IMAGE_WEBP=ON -DSDL2IMAGE_AVIF=OFF -DSDL2IMAGE_JXL=OFF \
     -DSDL2IMAGE_BACKEND_STB=ON \
     -DSDL2_INCLUDE_DIR=$SDL2_PKG/include/SDL2 -DSDL2_LIBRARY=$SDL2_PKG/lib/libSDL2.a
   ```

3. **编译**：`make -j1` → `libSDL2_image.a`（静态）+ `testimage`。

4. **上游测试**：`ctest --output-on-failure` → 1/1 通过（testimage，SDL_VIDEODRIVER=dummy + REQUIRE_LOAD_* 官方 CI 断言集，AVIF/JXL 关闭）。

5. **配方**：conan-init 后重写 conanfile.py 为 CMake 版，conan create 本地验证通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS | E092 | CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64 |
| 2 | SDL2 找不到 | sdl_find_sdl2 回退 FindPrivateSDL2 模块 | 注入 SDL2_INCLUDE_DIR/SDL2_LIBRARY |
| 3 | `webp/decode.h` 找不到 | webp_INCLUDE_PATH 指到 include/webp | 改为 include 根（含 webp/ 子目录） |
| 4 | libtiff.so 运行时报符号缺失 | LD_LIBRARY_PATH 缺 libjpeg/zstd | conanrun 环境提供完整传递依赖 |
| 5 | TIFF::TIFF 目标不存在 | libtiff 配方暴露 TIFF::tiff | CMakeDeps set_property cmake_target_name |

## 源码修改

无源码补丁（patches 为空），全部通过 CMake 选项与注入变量完成 OHOS 适配。

## 依赖版本

- sdl2/2.30.10
- libtiff/4.7.2
- libwebp/1.6.0

## 验证结果

```bash
$ ctest --output-on-failure
1/1 Test #1: testimage ... Passed (1.09 sec)
100% tests passed, 0 tests failed out of 1

$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# PASS（含 test_package 消费者测试 IMG_Init/IMG_Load_RW）
```
---

**编译结束**: 2026-08-29 01:35
**最终状态**: built
