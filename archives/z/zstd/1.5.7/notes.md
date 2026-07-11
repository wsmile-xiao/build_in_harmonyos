# zstd 1.5.7 编译笔记（HarmonyOS PC · Conan cmake）

## 定位
- Zstandard 快速压缩库；本次作为 **libtiff 的 Conan 依赖**（Zstd codec）适配。
- 产出 `libzstd.so`（SONAME `libzstd.so.1`）。`package_info.libs = ['zstd']`，无外部依赖。

## 构建方式（glfw/libjpeg-turbo 同法：自发现 toolchain + 裸 cmake）
`build()` 里 `_ohos_toolchain()` 自发现 `ohos.toolchain.cmake` + 裸 `cmake -B ... -DCMAKE_TOOLCHAIN_FILE=<它>`
构建（**不经 conan_toolchain**，故 recipe 自包含、不依赖 CI profile host 段，裸 `conan create` 即可）。要点：
- **CMakeLists 在 `build/cmake` 子目录**（`-S <source>/build/cmake`）。
- `-DCMAKE_INSTALL_LIBDIR=lib`：ohos.toolchain 64 位默认 `lib64/`，须强制 `lib/`。
- `-DZSTD_BUILD_SHARED=ON -DZSTD_BUILD_STATIC=OFF -DZSTD_BUILD_PROGRAMS=OFF -DZSTD_BUILD_TESTS=OFF`。
- `package()` 调 `_sign_shared_libs()` 重签 `.so`。

## 真机踩坑：musl 无 GNU qsort_r（zstd 专有，libjpeg-turbo 没这个）
`ld.lld: error: undefined symbol: qsort_r`（cover.c 的 COVER_ctx_init）。zstd 的 `lib/dictBuilder/cover.c`
与 `lib/common/zstd_deps.h` 在 `__linux__` 下自动 `#define _GNU_SOURCE` → 走 glibc `qsort_r`；但 **OHOS 是
musl，不提供 GNU qsort_r**。上游本就为 `__ANDROID__`（"NDK doesn't ship qsort_r()"）开了例外——OHOS 同理。
**修法（已进 recipe，`build()` 的 `_patch_gnu_qsort_r()`）**：给两处守卫加 `&& !defined(__OHOS__)`
（真机确认 `__OHOS__=1`），令其走 C90 fallback（全局 ctx + 普通 `qsort`）。libtiff 只用 ZSTD 压/解，不碰
ZDICT dictBuilder，此改零影响。

其余沿用 libjpeg-turbo 的处理：自发现 toolchain（ML-0035）、`CMAKE_INSTALL_LIBDIR=lib`（避 lib64）、
`_sign_shared_libs()` 重签、离线源码（download_cache 按 sha256）。

## 状态
**built（真机已验，CI-portable）** — 2026-07-11 在 HarmonyOS PC(2in1, 3QC0124C11000718, ohos-sdk 26.0.0.18)
**裸** `conan create -pr ohos-native`（不带 -c:h）通过：test_package `dlopen libzstd.so ok`，产物
`lib/libzstd.so.1.5.7` **SONAME=libzstd.so.1**，DT_NEEDED 仅 `libc.so`，`.so` 已 selfSign。
