# opencsg 1.8.2 适配笔记

## 编译环境

- 上游版本: OpenCSG 1.8.2（tag `opencsg-1-8-2-release`，2026-02-08 发布）
- Conan 包版本: `opencsg/1.8.2`（与上游一致，未递增后缀）
- 构建系统: cmake
- 编译日期: 2026-09-11
- 编译器: clang / clang++ 15.0.4（OHOS SDK / DevEco Studio）
- 目标三元组: aarch64-linux-ohos
- 状态: built（本机交叉编译 + 真机 shadow CI 全部门禁通过；制品仓发布尚未执行）
- 难度: B-candidate（路径 A 基础适配 + 路径 B 贡献创新；最终由评审判定，见 PATH_B_CANDIDATE.md）

## 编译步骤

本机前置验证（未使用 Conan，用 OHOS SDK 工具链等价复现配方行为）：

```bash
# 1. 取上游官方 tag 归档
curl -fsSL -o opencsg-1.8.2.tar.gz \
  https://github.com/floriankirsch/OpenCSG/archive/refs/tags/opencsg-1-8-2-release.tar.gz
sha256sum opencsg-1.8.2.tar.gz   # 63c74513f8197ceaef68bd90502c096b64146997d67e0979a82e0e8db2928527

# 2. 解压并应用补丁（与 conan build() 的 apply_conandata_patches 等价）
tar -xzf opencsg-1.8.2.tar.gz
cd OpenCSG-opencsg-1-8-2-release
patch -p1 < .../patches/0001-glad-ohos-opengl-loader.patch
patch -p1 < .../patches/0002-src-CMakeLists-optional-opengl-lookup.patch

# 3. 用 OHOS 工具链配置（等价于 CMakeToolchain + ohos-aarch64 profile）
cmake -S . -B build -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_SDK/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a -DOHOS_STL=c++_shared \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLE=OFF -DBUILD_SHARED_LIBS=ON

# 4. 编译
cmake --build build --parallel
```

配方在 CI 中的实际入口：

```bash
conan create archives/o/opencsg/1.8.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could NOT find OpenGL (missing: OPENGL_opengl_LIBRARY OPENGL_glx_LIBRARY)`，configure 失败 | `src/CMakeLists.txt` 调用 `find_package(OpenGL REQUIRED)`，但 `opencsg` 目标并不链接 GL（GL 由自带 glad 运行时 dlopen）；HarmonyOS 无桌面 GL 开发包 | `patches/0002`：改为 `find_package(OpenGL)`（可选）。其他平台仍正常查找，行为向后兼容 |
| 2 | glad 在 OHOS 上找不到桌面 GL 入口 | glad 的 dlopen 候选只有 `libGL.so.1` / `libGL.so`（及 Cygwin 名），OHOS 无这些名字；且 OHOS 的 `eglGetProcAddress` 在 `libEGL.so` 而非 GLX | `patches/0001`：候选列表追加 `libGLv4.so`；过程地址助手在 `glXGetProcAddressARB` 取不到时回退 `libEGL.so` 的 `eglGetProcAddress`。**采用 POSIX 通用写法，不引入平台宏**（R8/PF5）；仅用 glad 自带的 `GLAD_PLATFORM_*` 做编译期守卫 |
| 3 | 真机 shadow CI：`/system/bin/sh: cmake: inaccessible or not found`（conan build 阶段 Error 127） | hnp 工具链的 cmake/make/ninja 在 `/data/service/hnp/bin`，但该目录不在 CI 运行的 PATH 上。隔离 runner 生成的 `run-conan-heavy.sh` 未把 hnp bin 注入 PATH——**运行环境问题，非配方问题**（同设备其它可用 job 的 run 脚本都显式把 `/data/service/hnp/bin` 放进 PATH 并传给 runner 的 `--path`） | 不改基础设施脚本；改用与既有 job 一致的调用方式：`export PATH=...:/data/service/hnp/bin:...` 且 `ohos-test-runner.sh --path ...:/data/service/hnp/bin:...`。修正调用后 `conan create` 通过 |
| 4 | 设备构建的 `libopencsg.so` 无 SONAME（本机 Ninja 构建有 `libopencsg.so.1`）；消费者二进制 NEEDED 记录为绝对路径 | 目标属性 `VERSION/SOVERSION` 已正确解析（PROJECT_VERSION=1.8.2、MAJOR=1），但 OHOS 上 CMake 无 `Platform/HarmonyOS.cmake`（日志：`System is unknown to cmake`），平台规则缺失导致不生成版本化命名与 `-Wl,-soname`。最小复现（`project(t LANGUAGES CXX VERSION 1.8.2)` + `SOVERSION 1`）在设备上同样只产出无 SONAME 的 `libt.so`；对比 autotools 构建的 `libpam.so` 有 `libpam.so.0` | **这是设备 CMake 的全局限制，影响所有 CMake 共享库，非本库补丁所致**，且 CI 不接受也不检查该差异。不为此在单库 PR 内做平台级 hack；记录为已知限制，待基础设施补齐 `Platform/HarmonyOS.cmake` 或统一在 toolchain 注入 soname |

## 源码修改

`patches/0001-glad-ohos-opengl-loader.patch`（`src/glad/src/gl.cpp`）：

- `glad_gl_dlopen_handle()` 的 `NAMES[]` 追加 `"libGLv4.so"`（保留原有 `libGL.so.1` / `libGL.so` 在前，向后兼容）。
- 新增 `glad_gl_egl_dlopen_handle()`（由 glad 自带的 `GLAD_PLATFORM_APPLE` / `GLAD_PLATFORM_WIN32` 守卫，非平台宏）：打开 `libEGL.so` 并进程内常驻，避免提供入口点的库被提前卸载。
- `glad_gl_build_userptr()`：过程地址助手先取 `glXGetProcAddressARB`，**取不到时回退** `libEGL.so` 的 `eglGetProcAddress`。

> 该补丁**不引入 `__OHOS__` 等平台宏**（遵 iron-rules R8 / preflight PF5），对所有平台按“GLX 优先、EGL 兜底”的 POSIX 通用逻辑工作；未命中的 GL 入口点仍由 glad 原有的 `dlsym` 路径兜底。

`patches/0002-src-CMakeLists-optional-opengl-lookup.patch`（`src/CMakeLists.txt`）：

- `find_package(OpenGL REQUIRED)` → `find_package(OpenGL)`，并加注释说明原因。补丁不含 `#ifdef __OHOS__`，对所有平台都是"可选查找"，不破坏其他平台逻辑（R8）。

## 依赖版本

- 编译期 Conan 依赖: 无
- 运行期依赖: 设备侧 `libGLv4.so`、`libEGL.so`；C++ 运行时 `libc++_shared.so`
- 测试/示例: `example/` 需 GLUT，已 `BUILD_EXAMPLE=OFF`

## 验证结果

本机前置验证（Windows + OHOS SDK clang 15.0.4 交叉编译到 aarch64-linux-ohos）：

```text
configure: Could NOT find OpenGL (missing: ...)  ← 0002 生效后仅为提示，不再致命
build:     [18/18] Linking CXX shared library src/libopencsg.so.1.8.2   成功
产物:      libopencsg.so.1.8.2  ELF 64-bit LSB shared object, ARM aarch64, 521208 bytes
           SONAME = libopencsg.so.1
DT_NEEDED: libc++_shared.so, libc.so      ← 无任何 GL 链接依赖（符合设计）
导出符号:  885 个 OpenCSG 符号（含 render / Primitive 构造析构 / setOption / setContext）
补丁标记:  二进制内可见 libGLv4.so / libEGL.so / eglGetProcAddress 字符串
test_package: test_opencsg.cpp 交叉编译并链接成功
           ELF aarch64 PIE, interpreter /lib/ld-musl-aarch64.so.1, 24968 bytes
           DT_NEEDED: libopencsg.so.1, libc++_shared.so, libc.so
           未定义且由 libopencsg.so.1 解析的 OpenCSG 符号 13 个（含 Primitive 类型信息）
```

真机 shadow CI（HarmonyOS aarch64 设备，隔离 job + `ohos-test-runner.sh --mode heavy`，全部门禁通过、exit code 0）：

```text
L0_RESULT=pass: all checks passed          ← 含 L0j 版本占用、L0k 库类型、L0m/L0n 目录与分支
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir                ← 纯库，正常跳过
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
L1e: Negative test confirmed — test genuinely depends on opencsg   ← 移走 lib/ 与 include/ 后测试失败
conan create: opencsg/1.8.2 — passed

test_package（设备上编译并运行已安装包）:
  OpenCSG version: OpenCSG 1.8.2 (0x0182)
  [ok] OPENCSG_VERSION_STRING reports 1.8.2
  [ok] OPENCSG_VERSION == 0x0182
  [ok] Primitive::setOperation/getOperation round-trips
  [ok] Primitive::setOperation restores Intersection
  [ok] Primitive::setConvexity/getConvexity round-trips
  [ok] Primitive::setBoundingBox/getBoundingBox round-trips
  [ok] setOption/getOption(DepthBoundsOptimization) round-trips
  [ok] setOption/getOption(AlgorithmSetting) round-trips
  [ok] setContext/getContext round-trips
  [ok] libGLv4.so exports glGetString              ← 设备侧 GL 入口库确认存在
  [ok] libEGL.so exports eglGetProcAddress
  test_opencsg: PASS

产物（设备 conan 包内）:
  lib/libopencsg.so  ELF shared object, 64-bit LSB arm64, 346560 bytes
  DT_NEEDED = [libc++_shared.so, libc.so]          ← 无 GL 链接依赖，符合设计
  885 个 OpenCSG 导出符号；二进制含 libGLv4.so / libEGL.so 字符串
  include/opencsg.h、licenses/copying.txt、licenses/gpl-2.0.txt、licenses/gpl-3.0.txt
```

未执行的验证（不得视为通过）：

- 制品仓 `conan upload` / release 流水线：本轮未执行。
- 真实 CSG 渲染（`render()` 的 Goldfeather/SCS + FBO/遮挡查询路径）：需应用侧提供真实 GL context，本轮未执行（`example/` 需 GLUT，构建时 `BUILD_EXAMPLE=OFF`）。
- 上游单元测试：OpenCSG 1.8.2 上游无单元测试套件，无可执行项。
- 已知限制：设备 CMake 缺 `Platform/HarmonyOS.cmake`，共享库无 SONAME（见上表问题 4）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libopencsg.so | 346560 | 共享库（设备 `conan create` 产物） |
| include/opencsg.h | — | 公开头文件 |
| licenses/copying.txt, gpl-2.0.txt, gpl-3.0.txt | — | 许可证 |

> 本机与设备构建产物均不入 Git；正式发布由 CI `conan create` + `conan upload` 完成。

## 注意事项

- OpenCSG 自带 glad 是上游"私有拷贝"（符号收入 `OpenCSG` 命名空间），不要替换为系统 glad/glew，否则会与上游命名空间约定冲突。
- `render()` 的真实渲染、FBO/遮挡查询路径只能在有真实 GL context 的真机上验证；本机只能验证到编译/链接/静态符号层面。
- 设备上若不存在 `libGLv4.so`，`initExtensionLibrary()` 会静默失败（`gladLoaderLoadGL` 返回 0），届时需要确认设备 GL 能力或改走 GLES/EGL 路径。
- 上游许可证为 GPL-2.0-or-later（`copying.txt`），下游集成需注意兼容性。

## 知识沉淀（路径 B / 贡献创新候选）

本库适配附带 7 对（14 个文件）可复用知识草稿，面向不同复用场景；最终 B 类由评审判定，
详见 `PATH_B_CANDIDATE.md` 与版本级 manifest 的 `path_b_candidate` 段。

| # | 草稿（`knowledge/drafts/`） | 复用场景 |
|---|---------------------------|---------|
| 1 | `opencsg-1.8.2-ohos-glad-desktop-gl-loader` | 桌面 GL 运行时 dlopen 型库在 OHOS 的适配（`libGLv4.so` + `libEGL.so`） |
| 2 | `opencsg-1.8.2-ohos-headless-context-dependent-test-contract` | 无头 CI 下需 GPU/设备上下文的库如何写通过 R34/L1e 的真测试 |
| 3 | `opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path` | 隔离 job hnp 工具链不在 PATH（`cmake: Error 127`）的定位与正确调用惯例 |
| 4 | `opencsg-1.8.2-ohos-cmake-missing-platform-soname` | OHOS CMake 缺 Platform → 共享库无 SONAME（含最小复现与平台级判定） |
| 5 | `opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs` | `DT_NEEDED` 断言运行时加载型库未误链系统同名库（R26 自查） |
| 6 | `opencsg-1.8.2-upstream-tag-name-vs-version-archive-selection` | 上游 tag 名≠版本号时的归档选择 + 干净 `.tar.gz` basename |
| 7 | `opencsg-1.8.2-make-jobserver-mkfifo-not-permitted` | `make jobserver mkfifo: Operation not permitted` 非致命判据 |
