# DRAFT-sdl2-image-2.8.12-webpdemux-target-bridge

WebP::webpdemux target 缺失 → CMakeDeps build-module 注入（OHOS 交叉编译）
Conan 2.29.1 + OHOS aarch64 + clang 15 + SDL2_image 2.8.12

- **ID**: DRAFT-sdl2-image-2.8.12-webpdemux-target-bridge
- **触发工具**: cmake
- **阶段**: compilation
- **严重度**: 🔴 blocking (3)
- **分类**: cmake, conan, cross-compile, sdl2, libwebp

---

## 问题（Problem）

libwebp 配方 `package_info()` 仅暴露 `WebP::webp`（`cmake_target_name=WebP::webp`），但上游 SDL2_image 2.8.12 在 `SDL2IMAGE_WEBP=ON`、`SDL2IMAGE_DEPS_SHARED=OFF` 时执行 `target_link_libraries(SDL2_image PRIVATE WebP::webp WebP::webpdemux)`，同时链接两个 target；`libwebpdemux.so` 实际随 libwebp 包分发（`lib/libwebpdemux.so.2.0.17`），却未作为组件/独立 target 暴露。

Conan 2 的 CMakeToolchain 默认 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`，使 `find_package(webp)` 命中 CMakeDeps 生成的 `WebPConfig.cmake`（仅定义 `WebP::webp`），而非上游 `cmake/Findwebp.cmake` 模块（该模块本会同时定义 `WebP::webp` 与 `WebP::webpdemux` 两个 IMPORTED target）→ 配置期报：

```
Target "SDL2_image" links to:
  WebP::webpdemux
but the target was not found.
```

另：`Findwebp.cmake` 的 `find_path(webp_INCLUDE_PATH NAMES webp/decode.h)` 需要 include 根（含 `webp/` 子目录），错误指到 `include/webp` 会报 `webp/decode.h not found`。

**错误特征**：`Target "SDL2_image" links to:.*WebP::webpdemux` | `but the target was not found` | `webp/decode.h not found`

---

## 根因（Root Cause）

上游直接链接 `WebP::webp` 与 `WebP::webpdemux` 两个 target，而 libwebp 的 Conan 配方只暴露 `WebP::webp`；`libwebpdemux.so` 存在但未映射为 target。加上 `PREFER_CONFIG=ON` 使 `find_package(webp)` 走 CMakeDeps config（只定义 `WebP::webp`），上游 `Findwebp.cmake` 模块（会补 `WebP::webpdemux`）不被加载 → target 缺失。

**影响范围**：消费 libwebp 且上游直接链接 `WebP::webp` 与 `WebP::webpdemux` 的 CMake 项目（SDL2_image 2.6.0+/2.8.x、SDL_image 系），在 OHOS/aarch64 交叉编译 + Conan 2 CMakeDeps（`PREFER_CONFIG=ON`）下构建的场景。

---

## 方案（Solution）

conan-recipe build-module imported-target injection（`cmake_build_modules`）：

1. `generate()` 中为 libwebp 依赖注入一个 build module（`cmake_build_modules`），其中定义缺失的 `WebP::webpdemux` UNKNOWN IMPORTED target，`IMPORTED_LOCATION` 指向 libwebp 包内 `lib/libwebpdemux.so`；
2. 同时把 `webp_INCLUDE_PATH` / `webpdemux_INCLUDE_PATH` 缓存变量指向 libwebp include 根（含 `webp/` 子目录）。

这样 `find_package(webp)` 命中 CMakeDeps `WebPConfig` 时 `WebP::webpdemux` 已存在，无需改 libwebp 配方或改上游源码。

```python
def generate(self):
    deps = CMakeDeps(self)
    webp = self.dependencies["libwebp"]
    if webp.package_folder:
        module = os.path.join(self.generators_folder, "WebP-webpdemux.cmake")
        with open(module, "w", encoding="utf-8") as fh:
            fh.write("if(NOT TARGET WebP::webpdemux)\n")
            fh.write("  add_library(WebP::webpdemux UNKNOWN IMPORTED)\n")
            fh.write("  set_target_properties(WebP::webpdemux PROPERTIES\n")
            fh.write("      IMPORTED_LOCATION \"%s\")\n" % os.path.join(webp.package_folder, "lib", "libwebpdemux.so"))
            fh.write("endif()\n")
        deps.set_property("libwebp", "cmake_build_modules", [module])
    deps.generate()
    tc = CMakeToolchain(self)
    tc.cache_variables["webp_INCLUDE_PATH"] = os.path.join(webp.package_folder, "include")
    tc.cache_variables["webpdemux_INCLUDE_PATH"] = os.path.join(webp.package_folder, "include")
    tc.generate()
```

**回退方案**（priority 2）：disable WEBP backend —— 若 libwebp 包无法暴露 webpdemux 且无法注入 target，可 `SDL2IMAGE_WEBP=OFF` 并同步 `SDL_IMAGE_TEST_REQUIRE_LOAD_WEBP=0`，放弃 WEBP 格式支持（功能裁剪，非首选）。

**自动修复**: false；**实现层**: conan-recipe

---

## 验证（Verification）

- **失败证据（修复前）**：未注入 build-module 的配方 `conan create` 报 `Target "SDL2_image" links to: WebP::webpdemux but the target was not found`（G2 FAIL）。
- **通过证据（修复后）**：
  - conan-verify G2（conan create）/ G3（系统同名库隔离）PASS
  - W3 本地 CI 模拟 1/1、Pass rate 100%（含 L0i 依赖 registry 检查、L1 测试、L1e 负向验证、L4/L5）
  - 上游 `testimage` ctest 1/1 Passed（1.13s）
  - test_package 消费者测试 `IMG_Init/IMG_Load_RW` 内存 BMP 通过
- **路径实证**：`libwebpdemux.so.2.0.17` 实测存在于 libwebp 包 `lib/` 目录。

**验证命令**：
```bash
grep -nE 'WebP::webpdemux|webp_INCLUDE_PATH|cmake_build_modules' conanfile.py
grep -nE 'Target "SDL2_image" links to: WebP::webpdemux' reports/conan-create.log
```

---

## 查重（Deduplication）

- **similar_to**: E300（`cmake-cache-path-bridge`: FFTW Find module + CMakeDeps gap）；E092（CMake 不识别 HarmonyOS）；DRAFT-cdogs-sdl-sdl2-conan-cmake-bridge（SDL2 系 vendored Find 桥接）
- 本条目聚焦 libwebp 单依赖缺第二个 target（`WebP::webpdemux`）的注入，与 SDL2 系整套 vendored Find 桥接（cdogs）互补；E300 是通用 cache-path 桥接，本条目是 build-module target 注入实例。

---

## 适用边界（Applicability Boundaries）

消费 libwebp 且上游直接链接 `WebP::webp` 与 `WebP::webpdemux` 的 CMake 项目，在 OHOS/aarch64 交叉编译 + Conan 2 CMakeDeps（`PREFER_CONFIG=ON`）下构建；libwebp 配方未暴露 webpdemux 组件时通用。

### 禁止策略

| 模式 | 原因 | 后果 |
|------|------|------|
| `SDL2IMAGE_WEBP.*OFF` 掩盖缺失 | 只为过编译而关功能 | 丢失本可用的 WEBP 支持，非根因修复 |
| `webp_INCLUDE_PATH` 指到 `include/webp` | `find_path NAMES webp/decode.h` 需根 | `webp/decode.h not found` |
| 修改已发布 libwebp 配方/动其他库补 target | 依赖已发布不可改 | 破坏依赖链/跨库污染 |

---

## 元数据

- **doc_file**: knowledge/drafts/DRAFT-sdl2-image-2.8.12-webpdemux-target-bridge.md
- **last_updated**: 2026-08-29
- **source_event**: sdl2-image 2.8.12 OHOS CMake adaptation with Conan 2.29.1 CMakeDeps（R01/R06 实证）
- **authors**: junshi_liu
- **metrics**: success 1 / fail 1 / confidence 0.5 / last_used 2026-08-29
