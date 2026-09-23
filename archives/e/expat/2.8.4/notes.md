# expat 2.8.4 编译笔记（HarmonyOS PC）

## 本版是什么

纯上游版本 bump：`2.8.2` 线（配方 2.8.2.1.1，已合）→ 上游 `R_2_8_4`。配方结构、cmake
选项、签名与测试流程**逐字沿用已验证的 2.8.2.1.1 线**（目录：conanfile.py / conandata.yml /
test_package 整套拷入后仅改版本号与源码 sha256/url）。源码 sha256 由 R_2_8_4 归档实测：
`a8a9c5cbba9110000b13cc9943f50fcd7e552a5cbad49cb191142c500a0a11b7`。

沿用自 2.8.2.1.1 的配方背景（决定配方形态，非本版改动）：

- **为什么走「自发现 ohos.toolchain + 裸 cmake」**：`os=OHOS` 下 conan 的 `CMakeToolchain`
  把 `CMAKE_SYSTEM_NAME` 映射成 cmake 不认的值（ML-0035），产物**不带 SONAME、也无版本化软链**。
  链接器在被链库无 SONAME 时，会把该库的**路径**写进消费方 DT_NEEDED，使消费方不可重定位
  （fontconfig 链 2.8.2 产物后烤死 expat 包目录哈希，换环境即 `Error loading shared library`
  + 一串 `XML_* symbol not found`）。改用 SDK `ohos.toolchain.cmake` 后 cmake 正常产出 SONAME。
- **`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`**（2026-08-07 issue #1912 follow-up）：vips shadow
  CI 暴露设备文件系统无法 `cmake_symlink_library`（建 `libexpat.so.1` 软链 Permission denied），
  故出无版本号的 .so，同时保留 toolchain 的 `-Wl,-soname,` 避免 DT_NEEDED 路径污染。
- **`_sign_binaries()`**：cmake 走 SDK toolchain 产的 `.so` 自签无效（dlopen Permission denied），
  须 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign` 重签。

## 2.8.4 相对 2.8.2 的构建相关差异（已核对源码）

- CMake 仍提供 `EXPAT_BUILD_TOOLS/EXAMPLES/TESTS/DOCS/SHARED_LIBS/PKGCONFIG` 全组开关，
  `runtests` 目标仍设 `RUNTIME_OUTPUT_DIRECTORY tests` → 产物仍在 `build-ohos/tests/runtests`。
  故构建/测试路径零改动。
- **熵源开关默认值变化**：2.8.2 时代 `EXPAT_WITH_GETRANDOM` 默认 OFF（配方注释曾记录「expat 默认
  EXPAT_WITH_*=OFF 不启用任何源 → 运行期缺熵」）；2.8.4 的 `CMakeLists.txt` 改为
  `expat_shy_set(EXPAT_WITH_GETRANDOM "AUTO" ...)`（`default=AUTO`，再
  `evaluate_detection_results(... HAVE_GETRANDOM ...)` 自动探测）。本配方**仍显式 `=ON`**：
  与已验证 2.8.2 线行为一致、不随上游自动探测结果漂移（OHOS 交叉编译下探测口径可能与真机
  libc 实际能力存在差异，确定性覆盖更稳）。

## Upstream tests

沿用 2.8.2.1.1：`EXPAT_BUILD_TESTS=ON`，构建后对 `build-ohos/tests/runtests` 做
remove-section + 自签，再直接运行。这是 expat 自带完整 C 单测/回归 runner（内置 minicheck，
无外部下载）。非零退出即 fail `conan create`。2.8.2 线在 CI #21766 的实测口径：

```text
Expat version: expat_2.8.2
100%: Checks: 4824, Failed: 0
```

2.8.4 的**实际 check 数与通过率以本 PR 的 CI runner 输出为准**（版本 bump 可能增删 START_TEST），
验证结果段引用 CI 实跑输出，不从源码声明估算。上游测试源码不改、不排除。

## 下游影响

expat 无运行期依赖（`dependencies: []`），纯 C 库，本 bump 不牵连下游配方改动。版本 `2.8.4`
为真实上游新版本（仓库现存最高 2.8.2.x 线），非 R37 后缀递增场景。
