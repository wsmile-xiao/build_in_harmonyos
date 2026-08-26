# DRAFT-cdogs-sdl-sdl2-conan-cmake-bridge

vendored FindSDL2*.cmake ↔ Conan CMakeDeps 桥接（OHOS 交叉编译）
Conan 2.29.1 + OHOS aarch64 + clang 15

- **ID**: DRAFT-cdogs-sdl-sdl2-conan-cmake-bridge
- **触发工具**: cmake
- **阶段**: compilation
- **严重度**: 🔴 blocking (3)
- **分类**: cmake, conan, cross-compile, sdl2

---

## 问题（Problem）

cdogs-sdl 1.0.0 自带 vendored `build/cmake/FindSDL2.cmake / FindSDL2_image.cmake / FindSDL2_mixer.cmake`，用 find_path/find_library 解析 `SDL2_*` 变量。在 OHOS aarch64 交叉编译 + Conan 2 CMakeDeps 下：

1. 启用 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=TRUE` → `find_package(SDL2)` 走 CMakeDeps CONFIG，只定义 `sdl2::sdl2` target，不设置 `SDL2_INCLUDE_DIRS` 变量 → 上游 `include_directories(${SDL2_INCLUDE_DIRS})` 为空 → `SDL_audio.h`/`SDL_gamecontroller.h` not found
2. 关闭 PREFER_CONFIG 保持 MODULE（含 `generators=CMakeDeps` 时）→ MODULE 的 find_path/find_library 在交叉编译环境找不到 Conan 包内头文件，或返回裸库路径而不含传递依赖（libwebp/libtiff/zlib）→ 链接期 `undefined symbol`
3. 上游依赖 nanopb 的 `nanopb_generate_cpp` 宏（需 protoc + Python google.protobuf + pkg_resources），交叉环境工具缺失

**错误特征**：`SDL_audio.h file not found` | `SDL_gamecontroller.h file not found` | `undefined symbol: WebPGetFeaturesInternal` | `undefined symbol: TIFFClientOpen` | `undefined symbol: pb_decode` | `No rule to make target .*msg\.pb\.c`

---

## 根因（Root Cause）

上游 vendored Find 模块用变量式（`SDL2_INCLUDE_DIRS`/`SDL2_LIBRARY`）解析，而 Conan CMakeDeps 提供 target 式（`sdl2::sdl2`）。两者桥接缺失：MODULE 模式不填充传递依赖、CONFIG 模式不填充上游变量。全套问题不能靠参数开关/粒度替换解决——需要显式缓存变量桥接。

**影响范围**：携带 vendored FindFoo*.cmake 模块、用 find_path/find_library 解析 CMake 变量风格的 SDL2 系（或类似 FFmpeg/GStreamer/SDL 系）项目，在 OHOS/arm64 交叉编译 + Conan 2 CMakeDeps 下消费静态依赖的场景。

---

## 方案（Solution）

conan-recipe cache-variable bridge（E300 `cmake-cache-path-bridge` 扩展）：

1. conanfile.py `generate()` 中遍历 `self.dependencies[sdl2/sdl2_image/sdl2_mixer]`，将 `cpp_info.includedirs`（含 include/SDL2 子目录）与 `cpp_info.libs` 映射为上游 Find 模块期望的缓存变量（`SDL2_INCLUDE_DIRS`/`SDL2_LIBRARY`/`SDL2_IMAGE_*` 等），经 CMakeToolchain `cache_variables` 注入；库变量直接指向 CMakeDeps imported target（`sdl2::sdl2` 等）以携带 INTERFACE_LINK_LIBRARIES 传递依赖。**不设置 `CMAKE_FIND_PACKAGE_PREFER_CONFIG`**（避免 MODULE→CONFIG 变量丢失回归）。

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    for dep, prefix in ((self.dependencies["sdl2"], "SDL2"),
                        (self.dependencies["sdl2_image"], "SDL2_IMAGE"),
                        (self.dependencies["sdl2_mixer"], "SDL2_MIXER")):
        inc = "".join(...)  # cpp_info.includedirs + include/SDL2 子目录
        tc.cache_variables[f"{prefix}_INCLUDE_DIR"] = inc
        tc.cache_variables[f"{prefix}_INCLUDE_DIRS"] = inc
        tgt = dep.ref.name + "::" + dep.ref.name
        tc.cache_variables[f"{prefix}_LIBRARY"] = tgt
        tc.cache_variables[f"{prefix}_LIBRARY_TEMP"] = tgt
        tc.cache_variables[f"{prefix}_LIBRARIES"] = tgt
    tc.generate()
```

2. build() 中再对源做三处补丁：
   - (a) 顶层 CMakeLists.txt 注入 `find_package(sdl2/sdl2_image/sdl2_mixer/nanopb CONFIG QUIET)` + `add_definitions(-Wno-implicit-const-int-float-conversion)`（clang 15 RAND_MAX 转换）
   - (b) src/proto/CMakeLists.txt：`msg.pb.c/.h` 已预生成时跳过 `nanopb_generate_cpp`（避免 protoc/Google protobuf 依赖），并给 `cdogs_proto` 追加 `target_link_libraries(cdogs_proto nanopb::nanopb)`
   - (c) src/cdogs 与 src/tests 的 `target_link_libraries` 保留上游 MODULE 变量并追加 CMakeDeps targets（`sdl2::sdl2 sdl2_image::sdl2_image ...`）

**回退方案**（priority 2）：conan-toolchain pkg-config bridging —— 若目标和依赖可用 pkg-config，由 `pkg_check_modules` 替代 find_path，配合 pkg-config 文件 `Libs.private` 传递静态依赖。

**自动修复**: false；**实现层**: conan-recipe

---

## 验证（Verification）

- **conan-verify**：r10 通过（G1-G4 + L2/L4/L5 全 PASS）；r11 再验（W3 L0d self.run() 门禁、交叉编译 test() 用 file/strings 断言）
- **原生 OHOS CTest**（pc3-1, HongMeng Kernel 1.12.0）：
  - r19 未配置库路径：10 测试 3 通过/7 失败（首错缺 libtiff.so.6）
  - r20 配置 `LD_LIBRARY_PATH`（27 个 Conan 包 lib 目录）：10 测试 9 通过/1 失败（autosave SegFault，相对路径问题），90%
  - r21 以源目录为工作目录重跑 autosave_test：exit 0，3 features/6 scenarios 全通过（含 campaign save/load 断言）
  - 原生 CTest 实际 10/10 通过（pic_test 上游禁用单独计数）
- **运行时**：cache-variable bridge 使 SDL2 系传递依赖（libtiff/libwebp/libsharpyuv/libjpeg/zstd）在原生 OHOS 运行时可用；需配置 `LD_LIBRARY_PATH` 指向 Conan 包 lib 目录

**验证命令**: `grep -R 'SDL2_INCLUDE_DIRS\|SDL2_LIBRARY\|SDL2_IMAGE_LIBRARIES\|nanopb_generate_cpp' CMakeLists.txt src/`

---

## 查重（Deduplication）

- **similar_to**: E300（`cmake-cache-path-bridge`: FFTW Find module + CMakeDeps gap）；E225（test_package CMakeUserPresets.json: user_presets_path=False + build_folder=$TMP）
- 本条目为 SDL2 系实例化，含原生 CTest 验证证据与 nanopb 预生成守卫

---

## 适用边界（Applicability Boundaries）

携带 vendored FindFoo*.cmake 模块、用 find_path/find_library 解析 CMake 变量风格的项目（SDL2 系 / FFmpeg / GStreamer 等），在 OHOS/arm64 交叉编译 + Conan 2 CMakeDeps 下消费静态依赖的场景。

### 禁止策略

| 模式 | 原因 | 后果 |
|------|------|------|
| `CMAKE_FIND_PACKAGE_PREFER_CONFIG.*TRUE` | 把 MODULE 解析导向 CONFIG，变量丢失 | SDL_audio.h not found（r08 实测） |
| 清空/裸库替换 `${SDL2_IMAGE_LIBRARIES}` | 丢失传递依赖 | undefined symbol: WebP*/TIFF*（r08 实测） |
| 手动伪造 msg.pb.c 而非用上游预生成 | 上游已带预生成产物 | nanopb 生成失败/产物不一致 |

---

## 元数据

- **doc_file**: knowledge/doc/DRAFT-cdogs-sdl-sdl2-conan-cmake-bridge.md
- **last_updated**: 2026-08-26
- **source_event**: cdogs-sdl 1.0.0 r08-r10 OHOS CMake adaptation with Conan 2.29.1 CMakeDeps
- **authors**: junshi_liu
- **metrics**: success 1 / fail 6 / confidence 0.143 / last_used 2026-08-26