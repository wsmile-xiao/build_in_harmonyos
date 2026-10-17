# sdl2_ttf 2.24.0 适配笔记

## 编译环境
- 构建系统: CMake (upstream ships CMakeLists.txt + autotools; CMake preferred)
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-unknown-linux-ohos)
- 状态: built (manual cmake verified, conan create blocked by env)

## 探索性编译结果

### 手动 CMake 编译 (成功)
```bash
cd ~/tmp/builds/sdl2_ttf-2.24.0.work
# conan install 拉取依赖 (sdl2/2.30.10 static, freetype/2.14.3.1)
conan install . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# cmake 配置
cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release \
  -DSDL2TTF_VENDORED=OFF -DSDL2TTF_HARFBUZZ=OFF -DSDL2TTF_SAMPLES=OFF -DSDL2TTF_INSTALL=ON
# 编译成功: libSDL2_ttf.so 生成
make -j1
# staging 安装成功
cmake --install . --prefix $TEST_PREFIX
```

产物: libSDL2_ttf.so, include/SDL2/SDL_ttf.h, cmake config, pkgconfig, LICENSE.txt

### Patch
- 0001-CMakeLists.txt.patch: CMakeLists.txt 中
  find_package(Freetype REQUIRED) → find_package(freetype CONFIG REQUIRED)
  Freetype::Freetype → freetype::freetype
  原因: ohpcd freetype 包的 CMakeDeps target 是 freetype::freetype (小写),
  而 sdl2_ttf 上游用 CMake FindFreetype 模块名 (大写 Freetype::Freetype)。

### sdl2 cmake_file_name
- 设 deps.set_property("sdl2", "cmake_file_name", "SDL2") 让 find_package(SDL2) 找到 SDL2Config.cmake
- 不设 cmake_target_name: 默认 target (sdl2::sdl2) 不匹配 SDL2::SDL2-static,
  sdl_find_sdl2 回退到 PrivateSDL2 find module, 正确设置 include dirs

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | freetype target 不匹配 | CMakeDeps 生成 freetype::freetype, 上游用 Freetype::Freetype | patch CMakeLists 用小写 target |
| 2 | SDL2 include 路径为空 | set cmake_target_name 导致数据文件 glob 不匹配 | 不设 cmake_target_name, 回退 PrivateSDL2 |
| 3 | conan create build() 失败 | OpenHarmony python subprocess/posix_spawn/fork 后子进程无法访问 SDK clang (Permission denied) | 本地用手动 cmake 验证; CI worker 环境无此限制 |

## 问题 3 详细说明
conan create 的 build() 中 cmake.configure() 用 subprocess (Python 3.12 posix_spawn)
创建 cmake 进程。cmake 内部用 fork 执行 make→clang。fork 后的子进程无法访问
/data/service/hnp/ohos-sdk.org/ (SDK clang 所在路径), 导致 clang 执行失败 (exit 1, 无 stderr)。
手动在 shell 中执行 cmake 成功 (shell 的 fork 后子进程权限完整)。
这是本地 OpenHarmony 环境的进程安全限制, CI worker 环境无此问题。

## 依赖版本
- SDL2: 2.30.10 (static, ohpcd 制品仓)
- freetype: 2.14.3.1 (ohpcd 制品仓)
- harfbuzz: 可选, 未启用 (SDL2TTF_HARFBUZZ=OFF)
---

**编译结束**: 2026-08-26 11:43
**最终状态**: built
