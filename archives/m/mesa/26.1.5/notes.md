# mesa 26.1.5 适配笔记（上游 Mesa 26.1.5，HarmonyOS PC）

## 版本说明

- Conan 包版本：`26.1.5`
- 上游源码版本：`26.1.5`（Conan 包版本与上游一一对应，**真版本升级**）
- 上游源码：官方 release tarball `https://archive.mesa3d.org/mesa-26.1.5.tar.xz`
  （SHA-256 `79e421c7ce18cd9e790b8375920325779f10798630bf30e0b22f1a21c8617122`，已核验）
- 同名前序配方：`24.3.4` / `24.3.4.1.1`（OSMesa 路线）。本版本是大版本跨越（24 → 26）。

### 与 24.3.4 系列的关键差异：上游已移除 OSMesa

上游 Mesa 在 **25.1.0** 移除了 OSMesa：

- `docs/relnotes/25.1.0.rst`：“Remove osmesa”
- `docs/relnotes/25.2.0.rst`：“meson: remove unused osmesa option”

26.1.5 源码树中**已不存在** `-Dosmesa` 选项，也不存在 `src/gallium/targets/osmesa`
目标。因此本版本不再交付 `libOSMesa`，改为交付 OHOS 桌面图形栈实际消费的组合：

| 制品 | 用途 |
|------|------|
| `libEGL.so.1` | EGL 1.5 入口（surfaceless + GBM 平台） |
| `libGLESv2.so.2` | OpenGL ES 2.0/3.x |
| `libGLESv1_CM.so.1` | OpenGL ES 1.1 |
| `libgbm.so.1` | GBM 缓冲管理 |
| `libgallium.so.26.1.5` | Gallium 驱动公共库 |

离屏渲染由 **EGL pbuffer / surfaceless + llvmpipe** 承担，用途与 OSMesa 等价
（headless 软件光栅化），且已是上游现行推荐路径。

## 编译环境

- 构建系统：meson（Conan `MesonToolchain`）
- 编译器：clang 15.0.4（OHOS 6.0 SDK，`aarch64-unknown-linux-ohos-clang`）
- 目标：OpenHarmony / HarmonyOS PC，aarch64，musl
- 运行验证：qemu-user（`qemu-aarch64-static` + OHOS musl 运行根）与 DAYU200 真机

## 交付配置

```
-Dplatforms=                    # 无 X11/Wayland，EGL 走内建 surfaceless
-Degl-native-platform=surfaceless
-Dgallium-drivers=softpipe,llvmpipe
-Dvulkan-drivers=
-Dgbm=enabled  -Degl=enabled   -Dglx=disabled
-Dopengl=true  -Dgles1=enabled -Dgles2=enabled
-Dglvnd=disabled
-Dllvm=enabled -Dlibunwind=disabled -Dvalgrind=disabled -Dzstd=disabled
-Dtools=
-Dbuild-tests=false            # 交付包只含运行时制品；测试用 -o mesa/*:build_tests=True
```

依赖：`expat/2.8.2.1.1`、`libdrm/2.4.133`、`llvm/20.1.0`、`zlib/1.3.1.1`；
构建期工具：`bison/3.8.2`、`flex/2.6.4.2`、`m4/1.4.19`。

## OHOS 适配点（补丁一览）

| 补丁 | 目标文件 | 作用 |
|------|----------|------|
| `0001-meson.build.patch` | `meson.build` | harmonyos 纳入 DRM/KMS 平台集合与 `_GNU_SOURCE` 列表；注入 `-fno-emulated-tls`；`/proc/self/exe` 进程名能力宏；测试关闭时 `nm` 非硬依赖 |
| `0002-bin-symbols-check.py.patch` | `bin/symbols-check.py` | 识别 HarmonyOS 平台，放行 OHOS 运行库符号（如 `__at_fini`） |
| `0003-src-util-u_process.c.patch` | `src/util/u_process.c` | 无 `program_invocation_name`/`getprogname` 的平台改读 `/proc/self/exe` |
| `0004-src-util-memstream.c.patch` | `src/util/memstream.c` | `u_memstream_close()` 在 `fclose` 前 `fflush`（musl/OHOS 语义） |
| `0005-src-meson.build.ohos-test.patch` | `src/meson.build` | 注册鸿蒙专项消费者端到端测试 target（源码 `src_additions/`，rule12） |
| `0006-exclude-libs-drm-symbols.patch` | `src/gbm/meson.build`、`src/egl/meson.build` | libgbm/libEGL 链接**静态** libdrm（`libdrm.a`）时加 `-Wl,--exclude-libs,ALL`，阻止 `drm*` 符号泄漏进动态导出表。**为何两处都要改**：libdrm 在 OHOS 以静态库交付，libgbm 链入后其 `drm*` 会进入导出表（上游 `gbm-symbols-check` 因此失败）；而 libEGL 也引用 11 个 `drm*` 符号、原先靠 libgbm 的导出表间接解析，若只在 libgbm 隐藏就会让 libEGL 在加载期解析失败。两处同时使用该 flag 后，各自内部的静态 libdrm 副本仍可内部解析。**实测**：libgbm `drm*` 导出 137 → 0（`gbm_*` 38 个保留）、libEGL `drm*` 导出 0（`egl*` 44 个保留，`eglGetProcAddress`/`eglGetPlatformDisplay`/`eglInitialize` 等入口点均在） |

## 遇到的问题与解决方案

| # | 问题（原始签名） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `clock_gettime` 隐式声明（strict C11） | meson.build 的 `_GNU_SOURCE` 注入列表不含 `harmonyos` | 平台列表加入 `harmonyos`（0001） |
| 2 | glapi 导出 `__emutls_*`，ABI-check 失败 | OHOS 工具链默认 emulated TLS；mesa 仅对 Android NDK 加 `-fno-emulated-tls` | 对 `harmonyos` 同样注入（0001） |
| 3 | `util_get_process_name()` 返回空串 | OHOS 无 `program_invocation_name`/`getprogname`，落入返回 `""` 的兜底分支 | 增 OHOS 分支读 `/proc/self/exe`（0003） |
| 4 | symbols-check 报额外导出 `__at_fini` | `platform.system()` 在 OHOS 返回 `HarmonyOS`，白名单未覆盖 | symbols-check 增加 HarmonyOS 分支（0002） |
| 5 | `u_printf`/memstream 测试输出为空 | OHOS `open_memstream()` 只在 `fflush()` 同步调用方缓冲区，`fclose()` 不更新 | `u_memstream_close()` 先 `fflush()`（0004） |
| 6 | `nm` 未找到导致 configure 失败 | `build-tests=false` 时 mesa 仍无条件查找 `nm`，OHOS worker 无 `nm` | 改为仅在启用测试时查找（0001） |
| 7 | `gbm-symbols-check` FAIL：`unknown symbol exported: drmXXX`（137 条） | OHOS 侧 `libdrm` 以**静态**库交付，`drm*` 目标文件被链入 `libgbm.so` 并进入动态导出表；libEGL 的 11 个 `drm*` 引用原先依赖 libgbm 的导出表间接解析 | `src/gbm/meson.build` 与 `src/egl/meson.build` 各加 `-Wl,--exclude-libs,ALL`（0006），使两个库各自内部解析其静态 libdrm 副本 |
| 8 | 上游测试全部 `SKIP (exit status 77)`，等于 0 用例执行 | Conan 交叉文件只写 `needs_exe_wrapper = true`，**不写 `exe_wrapper`**；meson 因此拒绝执行任何目标二进制 | `generate()` 在 `[binaries]` 段注入 `exe_wrapper = ['<qemu 包装器>']`（配方逻辑，非补丁） |
| 9 | meson 强制交叉失效：`unrecognized instruction mnemonic`（blake3 AVX-512 分支） | CI 用 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（同 profile），Conan 判为「非交叉」，只写 native 文件、无 `[host_machine]`，meson 误判 host 为 x86_64 | `generate()` 内 `self.conf.define("tools.build.cross_building:cross_build", True)`（配方逻辑） |
| 10 | host pkg-config 回落到宿主 x86_64 `libz.so`：`ld.lld: libz.so is incompatible with aarch64linux` | meson `dependency('zlib')` 未命中 OHOS 包时回落到宿主 | 显式 `self.requires("zlib/1.3.1.1")`（配方逻辑） |
| 11 | `Found pkg-config: NO` → `../meson.build:1848:15: ERROR: Dependency lookup for libdrm with method 'pkg-config' failed: Pkg-config for machine host machine not found` | conan 的 `MesonToolchain` 只认 `tools.gnu:pkg_config`，**不会**把 pkg-config 写进 `conan_meson_cross.ini` 的 `[binaries]`；meson 因此判定 host 机没有 pkg-config，expat/libdrm 全部 NOT FOUND | `_patch_meson_native()` 在 `[binaries]` 段注入 `pkgconfig = '<绝对路径>'`（配方逻辑） |
| 12 | `conan create` 全绿但产物跑不起来：`Error loading shared library libLLVM.so.20.1` / `Error relocating libgallium-26.1.5.so: ... symbol not found`（exit 127） | 交付动态库的 DT_NEEDED 跨出本包：`libgallium` → `libLLVM.so.20.1`、`libc++_shared.so`、`libexpat.so`；`libEGL` → `libgallium`、`libgbm`、`libexpat`。conan 只为**直接**依赖生成 runenv 条目，loader 找不到这些目录时进程在 `main()` 前就死 | `package_info()` 把 llvm/expat 的 libdir 与 OHOS SDK `libc++_shared.so` 目录一并注入 `runenv_info` 的 `LD_LIBRARY_PATH`（配方逻辑） |
| 13 | 消费者用例「通过」但**从未执行**（ZOMBIE TEST）：`test()` 里 `can_run(self)` 在 `-pr:b=default` 下恒为 False，直接 `return`，退出码 0 | `can_run()` 比较 build/host profile；OHOS aarch64 产物在 x86_64 宿主上恒为「不可运行」，与是否配了 qemu 无关 | `test_package/conanfile.py` 不再用 `can_run()`：从 `tools.cmake.cmaketoolchain:extra_variables` 取 `CMAKE_CROSSCOMPILING_EMULATOR`（无则回落已知 qemu 包装器），**无条件真跑**并把退出码作为结论；确实无包装器时用 `output.warning` 显式告警而非静默放行 |

## 鸿蒙特有测试（rule12）

`src_additions/gallium/tests/ohos/ohos_egl_e2e.c`（patch 0005 注册为 meson target）
是**消费者端到端**用例，不是纯断言：

1. **进程名适配**：调用 `util_get_process_name()`，验证返回可执行文件 basename
   （上游在 OHOS 会返回 `""`），并校验无路径分隔符。
2. **memstream 适配**：`u_memstream_open()` → 写入 → `u_memstream_close()`，
   **故意不调用 `fflush()`**，验证缓冲区在 close 后内容与长度均正确。
3. **真实渲染往返**：`eglGetDisplay` → `eglInitialize` → `eglChooseConfig` →
   `eglCreatePbufferSurface(64×64)` → `eglCreateContext(GLES2)` → `eglMakeCurrent`
   → 编译/链接顶点+片元着色器 → 绘制三角形 → `glReadPixels` 回读，
   断言绿色三角形像素数与红色清屏像素数均大于 0。

## 验证结果

- 构建：`conan create` 通过（meson `1080/1080` 目标全部链接成功）
- 消费者用例：`test_package` 经 qemu **真实执行**并全部通过
  （EGL 1.5 / `GL_RENDERER = llvmpipe (LLVM 20.1.0, 128 bits)` /
  `GL_VERSION = OpenGL ES 3.2 Mesa 26.1.5`，三角形 1352 绿像素 + 清屏 2744 红像素）
- 鸿蒙特有测试：`ohos_egl_e2e`（rule12）在 qemu 与 DAYU200 真机均通过
- 上游测试：见 PR 描述「验证结果」章节的实测数字

## 已知限制

- 上游 25.1.0 起不再提供 OSMesa；本包不交付 `libOSMesa`，桌面 OpenGL 固定管线
  需求应改用 EGL + GLES 或等待上游替代方案。
- 无 X11/Wayland/DRM 设备时仅软件光栅化（llvmpipe/softpipe）可用，无硬件加速。
- Vulkan 未构建（`-Dvulkan-drivers=`）。
