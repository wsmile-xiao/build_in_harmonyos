# filament 1.76.1 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://github.com/google/filament |
| tag | `v1.76.1` |
| 源码 sha256 | `f65b5b50ef5647a190b51a37fa006985e061bcfdc87c3b9b0ea18cf7b52042aa` |
| 构建系统 | CMake（≥3.22.1，`CMakeLists.txt:4`），**C++20**（`-std=c++20`，`:398,408`） |
| 编译器要求 | **必须是 clang**（`:351,356-361`；GCC 需 `FILAMENT_ENABLE_EXPERIMENTAL_GCC_SUPPORT=ON`，非 MSVC 的其他编译器直接 FATAL_ERROR） |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release |
| 依赖 | 无外部 Conan requires（third_party/ 全部内置） |
| 上游源码改动 | 一处：`CMakeLists.txt` 平台识别（见 §2.1）。由配方在 `build()` 内幂等就地写入，未以 unified diff 形式单独存放 |
| 包类型 | static-library（上游所有库都是显式 STATIC，见 §6） |
| 版本状态 | **本仓库首次适配 Filament**（此前无任何版本） |

## 1. 宿主工具 vs 目标库（专项规则的核心）

Filament 在**构建期执行**自己刚构建的程序来生成随后要链接进目标库的资源：

| 位置 | 执行 | 产物 |
|------|------|------|
| `filament/CMakeLists.txt:417` | `matc` | 编译材质 → `.filamat` |
| `filament/CMakeLists.txt:482` | `resgen` | 资源 blob |
| `filament/CMakeLists.txt:676` | `cmgen --ibl-dfg` | IBL DFG LUT |
| `filament/CMakeLists.txt:685` | `resgen -Z` | 资源 blob |
| `shaders/CMakeLists.txt:82,99` | `glslminifier`, `resgen` | shader 资源 |
| `libs/gltfio/CMakeLists.txt:105,118,125,167` | `matc`, `uberz`, `resgen` | gltfio 资源 |
| `libs/filagui/CMakeLists.txt:56,73` | `matc`, `resgen` | filagui 资源 |
| `libs/iblprefilter/CMakeLists.txt:53,63` | `matc`, `resgen` | iblprefilter 资源 |

上游为此提供了 `ImportExecutables` 两段式机制（`CMakeLists.txt:810-864`），
本配方完整采用，**两段都跑在同一台 OHOS 构建机上**：

```
第一段（宿主段） -DFILAMENT_EXPORT_PREBUILT_EXECUTABLES_DIR=<dir>
        → 以 IS_HOST_PLATFORM=TRUE 配置，构建
          matc/cmgen/resgen/filamesh/mipgen/uberz/glslminifier（aarch64 本机）
        → 写出 <dir>/ImportExecutables-Prebuilt.cmake
第二段（目标段） -DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=<dir>
        → 构建库本体，include 该文件取得工具 target，构建期直接执行它们
```

### 1.1 两个必须记住的坑

**(a) 构建主机就是执行主机，工具必须是 aarch64。** 本 farm 的验证设备是
**aarch64 HarmonyOS PC**（`uname -m` = aarch64），不是 x86_64 Linux。
因此**不能**用官方 Filament Linux 发行包（x86_64）里的工具充数——那些
二进制在这台机器上根本不能执行（`Exec format error`）。早期版本曾打包
`tools-x86_64-linux.tar.gz` 并在 `build()` 里解包，该做法已废弃并删除。

**(b) `<dir>` 必须相对源码目录。** `CMakeLists.txt:864`：

```cmake
set(IMPORT_EXECUTABLES ${FILAMENT}/${IMPORT_EXECUTABLES_DIR}/ImportExecutables-${IMPORT_EXECUTABLES_BUILD_TYPE}.cmake)
```

其中 `FILAMENT = ${CMAKE_CURRENT_SOURCE_DIR}`（`:343`）。传绝对路径会被拼成
`<src>/<abs path>`，直接报：

```
CMake Error at libs/filagui/CMakeLists.txt:30 (include):
  include could not find requested file:
    .../b//storage/.../b/build-release/host-tools/ImportExecutables-Prebuilt.cmake
```

本配方一律传 `os.path.relpath(<tools_dir>, self.source_folder)`（见
`_tools_export_rel()`）。

### 1.2 第一段如何只构建工具

第一段用 `subprocess` 直接驱动 CMake（工作目录独立于第二段：`<build>/host-tools`），
只构建 `TOOL_TARGETS` 七个目标；它们依赖的 filamat / glslang / spirv-tools /
spirv-cross / imageio / ibl 等库会作为依赖一并构建。并行度取
`tools.build:jobs`（子进程不会继承工具链里的 `CMAKE_BUILD_PARALLEL_LEVEL`，
所以显式取 profile 配置，本 farm 为 1）。

第一段的 configure 用 `-DFILAMENT_LINUX_IS_MOBILE=OFF`（否则
`IS_HOST_PLATFORM` 被清除，`CMakeLists.txt:1004` 的 `tools/` 子目录根本不会被
加入）与 `-DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=`（否则会试图导入它自己
正要构建的东西）。Conan 把 `tc.variables` 写成 `set(... CACHE ...)`，命令行
`-D` 已先行定义同名缓存项，故不会被工具链覆盖。

**已在设备上实测**（纯 configure，不编译）：第一段 configure 6.8 s 通过并写出
`<src>/host-tools-prebuild/ImportExecutables-Prebuilt.cmake`，其中 7 个工具均为
`add_executable(... IMPORTED GLOBAL)`；第二段 configure 9.7 s 通过，
`libfilament.a` / `filament` 目标存在。

## 2. 平台识别：`UNIX` / `LINUX`

### 2.1 为什么必须改上游（本配方唯一的源码改动）

CMake 不认识 `CMAKE_SYSTEM_NAME=HarmonyOS`，**不会设置 `UNIX`**（这正是
"System is unknown to cmake, create: Platform/HarmonyOS" 提示的由来）。
于是 `CMakeLists.txt:197`：

```cmake
if (UNIX AND NOT APPLE AND NOT ANDROID AND NOT WASM)
    set(LINUX TRUE)
else()
    set(LINUX FALSE)
endif()
```

令 `LINUX` 为 FALSE，configure 立刻死在：

```
CMake Error at libs/bluevk/CMakeLists.txt:19 (message):
  Platform not supported.  BlueVK supports Linux, Android, MacOS X, and Windows.
```

同时内置的 glslang 会走进 "unknown platform" 分支，丢掉
`OSDependent/Unix`（`glslang/glslang/CMakeLists.txt:36`、
`glslang/CMakeLists.txt:134`）。

配方 `_apply_ohos_unix_platform()` 在该判断**之前**插入：

```cmake
if (CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set(UNIX TRUE)
endif()
```

CMake 普通变量会被 `add_subdirectory` 继承，所以该设置同时到达 Filament
自身与全部 third_party 子项目。改动是幂等的（重复执行即 no-op）。

`LINUX=TRUE` 之后还需要关掉 Linux 分支里与桌面环境绑定、或与本平台 libc 不符的东西：

| 变量 | 位置 | 为什么 |
|------|------|--------|
| `FILAMENT_SUPPORTS_XCB` / `_XLIB` | `:64,:66` | 默认 ON；置 ON 会给 X11/XCB/XLIB 加编译宏（`CMakeLists.txt:212-235`），OHOS 没有这些窗口系统 |
| `FILAMENT_SUPPORTS_WAYLAND` | `:70` | 同上 |
| `USE_STATIC_LIBCXX` | `:431` | 默认 ON；clang 且非 glibc 时走 `set(CMAKE_CXX_FLAGS "... -static")`（`:446-448`），OHOS 是 musl，链接会失败 |

Vulkan 的 Linux 平台代码里 X11 部分由 `FILAMENT_SUPPORTS_X11` 宏保护
（`filament/backend/src/vulkan/platform/VulkanPlatformLinux.cpp:46`），
XCB/XLIB 关闭后不会引入任何 X11 头文件依赖。

### 2.2 `BUILD_SHARED_LIBS` 必须关闭

Filament 自己的库全部显式 STATIC，从不读 `BUILD_SHARED_LIBS`；但内置的
spirv-tools 会读，而 Filament 删掉了它的 `${SPIRV_TOOLS}-shared` 目标却保留了
引用它的 alias（`third_party/spirv-tools/source/CMakeLists.txt:343-359`，注释
"Always build ${SPIRV_TOOLS}-shared" 之上那一行已不存在）。于是
`BUILD_SHARED_LIBS=ON` 时 configure 报：

```
CMake Error at third_party/spirv-tools/source/CMakeLists.txt:359 (add_library):
  add_library cannot create ALIAS target "SPIRV-Tools" because target
  "SPIRV-Tools-shared" does not already exist.
```

本包因此声明 `package_type = "static-library"`，没有 `shared` 选项，
Conan 也就不会设置 `BUILD_SHARED_LIBS`；同时显式写 `-DBUILD_SHARED_LIBS=OFF`
把意图固定下来。

## 3. `FILAMENT_LINUX_IS_MOBILE` —— 必须设置且非常隐蔽

`CMakeLists.txt:249`：

```cmake
if (NOT ANDROID AND NOT WASM AND NOT IOS AND NOT FILAMENT_LINUX_IS_MOBILE)
    set(IS_HOST_PLATFORM TRUE)
endif()
```

OHOS 既不是 ANDROID/WASM/IOS，`FILAMENT_LINUX_IS_MOBILE` 默认 OFF（`:74`），
于是**朴素构建会被判成 host 平台**，走 `CMakeLists.txt:1004-1037` 的
`add_subdirectory(tools/...)` 并把 samples/libassimp/libpng 等一并拉进来。

**本配方设置 `-DFILAMENT_LINUX_IS_MOBILE=ON`**：清除 `IS_HOST_PLATFORM`，
进入使用导入工具的分支；副作用是 `MATC_TARGET` 由 `desktop` 变为 `mobile`
（`CMakeLists.txt:689-693`），即嵌入材质按 mobile shader family 编译——对
OHOS 是正确选择。

## 4. 后端选择（编译期决定）

| 选项 | 位置 | 默认 | 本配方 |
|------|------|------|--------|
| `FILAMENT_SUPPORTS_OPENGL` | `:593`（`add_definitions` `:594-596`） | ON | **ON** |
| `FILAMENT_SUPPORTS_VULKAN` | `:612`（非 WIN32/WASM/IOS 分支） | ON | **ON** |
| `FILAMENT_SUPPORTS_METAL` | `:628,:630` | 仅 Apple ON | OFF |
| `FILAMENT_SUPPORTS_WEBGPU` | 根目录无 `option()`，仅 android/*/CMakeLists 内声明 | 实际 OFF | OFF |
| noop | **不是选项，无条件编译** | 始终在 | 始终在 |

这些开关是**编译期**的：决定哪些 driver 被编入库，以及 matc 编译材质时
附加哪些 `-a <api>`（`CMakeLists.txt:697-708`）。保持 Vulkan+OpenGL 双开
可让嵌入材质同时带两套 shader family。

`libs/bluevk` 通过 **dlopen 运行时加载 libvulkan**（源码树里没有
vulkan-headers/vulkan-loader 依赖），所以"编译支持 Vulkan"与"运行时存在
可用 Vulkan 驱动/系统 surface"是两件事——后者属于运行环境，本阶段不涉及。

**noop 后端无条件编译**（`filament/backend/CMakeLists.txt:54-55`），
这使 test_package 能在无 GPU、无窗口的环境下真实创建 Engine 并跑完整帧循环。

## 5. 第三方依赖：全部内置，构建期零网络

`third_party/` 共 36 项（解包后约 1.2 GB），全部是**完整源码树**
（Filament 已从 git submodule 迁移到直接 vendored），**没有任何
FetchContent/ExternalProject/GIT_REPOSITORY/URL 下载**。

关键项：`glslang`(51M)、`spirv-tools`(29M)、`spirv-cross`(28M)、
`abseil`(19M)、`libsdl2`(65M，本配方 `FILAMENT_SKIP_SDL2=ON` 跳过)、
`libgtest`(4.6M，测试用)、`libz`、`zstd`、`libpng`、`imgui`、`civetweb`、
`robin-map`、`smol-v`、`stb`、`basisu`、`draco`、`tinyexr`、`libwebp`、
`dawn`(600M，仅 WebGPU 启用时才构建，本配方关闭)。

Filament **没有提供任何"用系统包替换 third_party"的 CMake 变量**，
所有依赖一律 `add_subdirectory(third_party/<name>/tnt)`。

## 6. 构建配置

```
-DCMAKE_BUILD_TYPE=Release
-DCMAKE_CXX_STANDARD=20
-DFILAMENT_LINUX_IS_MOBILE=ON
-DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=host-tools-prebuild   # 相对源码目录
-DFILAMENT_SKIP_SAMPLES=ON
-DFILAMENT_SKIP_SDL2=ON
-DFILAMENT_BUILD_TESTING=OFF
-DFILAMENT_SUPPORTS_VULKAN=ON
-DFILAMENT_SUPPORTS_OPENGL=ON
-DFILAMENT_SUPPORTS_METAL=OFF
-DFILAMENT_SUPPORTS_WEBGPU=OFF
-DFILAMENT_ENABLE_FGVIEWER=OFF
-DFILAMENT_ENABLE_MATDBG=OFF
-DFILAMENT_SUPPORTS_WEBP_TEXTURES=OFF
-DFILAMENT_SUPPORTS_XCB=OFF
-DFILAMENT_SUPPORTS_XLIB=OFF
-DFILAMENT_SUPPORTS_WAYLAND=OFF
-DFILAMENT_SUPPORTS_EGL_ON_LINUX=OFF
-DFILAMENT_SUPPORTS_OSMESA=OFF
-DUSE_STATIC_LIBCXX=OFF
-DBUILD_SHARED_LIBS=OFF
```

第一段额外使用（仅 configure 时覆盖）：

```
-DFILAMENT_LINUX_IS_MOBILE=OFF
-DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=
-DFILAMENT_EXPORT_PREBUILT_EXECUTABLES_DIR=host-tools-prebuild
```

## 7. 产物

Filament 安装 **约 39 个静态组件归档**到 `lib/`：`filament`、`backend`、
`filabridge`、`filaflat`、`math`、`utils`、`filamat`、`gltfio`、`gltfio_core`、
`ibl`、`ibl-lite`、`image`、`imageio-lite`、`ktxreader`、`geometry`、`uberzlib`、
`shaders`、`stb`、`zstd`、`perfetto`、`smol-v`、`meshoptimizer`、`basis_transcoder`、
`dracodec`、`mikktspace`、`civetweb`、`camutils`、`filameshio`、`matp` 等。

头文件分散安装（`install(DIRECTORY .../include DESTINATION include)` 与
`install(FILES ${DIST_HDRS} DESTINATION include/<target>)`），例如
`include/filament/`、`include/backend/`、`include/utils/`、`include/math/`。

**Conan 侧 `cpp_info.libs` 只声明主库 `filament`**——上游本身也没有
导出的 CMake package config，消费方需要按需链接组件归档
（test_package 的做法见 §8.2）。

## 8. 测试：诚实申报

### 8.1 上游测试（未运行，如实申报）

| 项 | 值 |
|----|----|
| 框架 | GoogleTest——**内置**（`third_party/libgtest`，非下载） |
| 规模 | `filament/test/*.cpp` 20 个；`libs/**/test*/*.cpp` 63 个；`libs/**/*_test.cpp` 1 个；`tools/**/tests/*.cpp` 2 个 |
| 目标 | `test_filament`（`filament/test/CMakeLists.txt:61`）、`test_depth`、`test_material_parser`；`test_compiler`/`test_framerate` 仅 Android |
| 启用条件 | `FILAMENT_BUILD_TESTING=ON` **且** `TNT_DEV`（即 Debug/RelWithDebInfo，见 `:587-590`） |
| 本次执行 | **未执行（NOT_RUN）** |

未执行的技术原因：

1. `test_filament` 目标只在 `FILAMENT_BUILD_TESTING=ON` **且**构建类型为
   Debug/RelWithDebInfo 时才被配置（`CMakeLists.txt:587-590` 的 `TNT_DEV`），
   而本包是 Release 交付；Debug 构建在单线程约束下耗时不可接受。
2. 即便构建出来，`test_filament` 链接的是**真实渲染路径**
   （`filament_rendering_test.cpp`、`depth_test.cpp`），需要可用的后端或
   显示环境；本阶段只有 noop 后端可用，不能覆盖该套件的全部用例。

如实申报 NOT_RUN，不把未运行的测试计为 PASS。

### 8.2 test_package（已执行，消费者视角）

`test_package/test_filament.cpp` 在 **noop 后端**上真实驱动引擎，12 个断言：

| # | 动作 | 断言 |
|---|------|------|
| 1 | `Backend::NOOP` 枚举值 | 存在（该构建包含 noop driver） |
| 2 | `Engine::create(Backend::NOOP)` | 非空 |
| 3 | `engine->getBackend()` | == `Backend::NOOP` |
| 4 | `engine->createRenderer()` | 非空 |
| 5 | `engine->createScene()` | 非空 |
| 6 | `engine->createView()` | 非空 |
| 7 | `engine->createCamera(entity)` | 非空 |
| 8 | `view->setScene(scene)` | 调用成功（上游为 setter-only API） |
| 9 | `view->setCamera(camera)` | 调用成功（同上） |
| 10 | `engine->createSwapChain(64, 64)` | 非空（离屏，无原生窗口） |
| 11 | `renderer->beginFrame(swapChain)` + `render(view)` + `endFrame()` | 完整帧循环执行成功 |
| 12 | `Engine::destroy(&engine)` | 句柄被清空 |

链接方式：test_package 的 `conanfile.py` 把依赖的 `package_folder` 传给
CMake，CMake 侧 `file(GLOB)` 收集 `lib/*.a` 并用
`-Wl,--start-group ... -Wl,--end-group` 链接全部组件归档
（组件间存在内部依赖，见 §7）。

测试二进制为 aarch64，在 OHOS PC 上原生运行，不需要 GPU 或窗口系统。

## 9. 本阶段的边界（如实记录，不含结论性判断）

- **已验证**：Filament 核心库（filament/backend/filabridge/filaflat/math/utils 等）
  能在 OHOS aarch64 上编译、链接，引擎可在 noop 后端上完成完整帧循环。
- **未验证**：Vulkan / OpenGL 后端在 OHOS 上的**实际运行**——这取决于设备侧
  是否存在可用的 Vulkan 驱动/loader 与显示 surface（`libs/bluevk` 是
  dlopen 运行时加载）。本阶段未做该验证，**不对其下任何结论**。
- 图形窗口展示不属于第一阶段目标。

## 10. 参考

- 上游：https://github.com/google/filament
- 官方 Linux 发行包（**本配方不使用**，仅供对照；其中的工具是 x86_64，
  在本 aarch64 设备上不可执行）：
  https://github.com/google/filament/releases/download/v1.76.1/filament-v1.76.1-linux.tgz

## 附录：pass 2 链接期 `-lbluegl` —— 0002 的 CMake 条件曾经是空操作

pass 1 全量通过（7/7 host tools + `libfilamat_combined.a` = 143360328 B），
pass 2 编译到 **100%**、`errors=0`，然后倒在**链接**阶段：

```
ld.lld: error: unable to find library -lbluegl
clang-15: error: linker command failed with exit code 1
make[2]: *** [filament/benchmark/CMakeFiles/benchmark_filament.dir/build.make:129:
             filament/benchmark/benchmark_filament] Error 1
```

即 `benchmark_filament` 的链接行里带着 `-lbluegl`，而 **pass 2 根本没有配置
`libs/bluegl`**（顶层 `CMakeLists.txt` 只在 `if (IS_HOST_PLATFORM)` 下
`add_subdirectory(${LIBRARIES}/bluegl)`），于是必然找不到该库。

### 根因：`OHOS` 不是这个工具链里的 CMake 变量

0002 早先的条件写的是

```cmake
AND (NOT OHOS OR IS_HOST_PLATFORM)
```

在构建机上实测：`conan_toolchain.cmake` 里

| 变量 | 出现次数 |
|---|---|
| `CMAKE_SYSTEM_NAME` | **0** |
| `OHOS` | **0** |
| `CMAKE_CROSSCOMPILING` | **0** |
| `CMAKE_SYSTEM_PROCESSOR` | **0** |

Conan 工具链的 `generic_system` 段是空的（没有 `set(CMAKE_SYSTEM_NAME …)`），
所以 `OHOS` 在 CMake 里**根本不是变量**，`NOT OHOS` 恒为 TRUE，
整条 `(NOT OHOS OR IS_HOST_PLATFORM)` 恒为 TRUE —— 这一处 CMake 改动
**始终没有生效**。（`gl_headers.h` 那一处用的是编译器宏 `defined(__OHOS__)`，
由 OHOS clang 预定义，真实有效；两者不能混为一谈。）

此前从未跑到链接阶段，所以这个空操作一直没有暴露：0002 实际只修好了编译期
的 GLES 头文件选择（pass 2 从 6% 推到 91%），链接期的问题留到了 100%。

### 修复：改用 `IS_HOST_PLATFORM`

`filament/CMakeLists.txt:259` 的定义是

```cmake
if (NOT ANDROID AND NOT WASM AND NOT IOS AND NOT FILAMENT_LINUX_IS_MOBILE)
    set(IS_HOST_PLATFORM TRUE)
endif()
```

也就是说 `IS_HOST_PLATFORM` 恰好是区分两个 pass 的那个信号，而 bluegl 作为
**host-only** 的 GL loader，上游本来就是在 `if (IS_HOST_PLATFORM)` 下加入的。
条件改为：

```cmake
if(FILAMENT_SUPPORTS_OPENGL
        AND NOT IOS
        AND NOT ANDROID
        AND NOT WASM
        AND IS_HOST_PLATFORM)
    target_link_libraries(${TARGET} PRIVATE bluegl)
endif()
```

| 构建 | `FILAMENT_LINUX_IS_MOBILE` | `IS_HOST_PLATFORM` | bluegl |
|---|---|---|---|
| OHOS pass 1（host tools） | OFF | TRUE | 链接（不变） |
| OHOS pass 2（target） | ON | 未设置（假） | **不链接**（修复点） |
| 桌面上游 Linux | OFF | TRUE | 链接（不变） |
| Android / iOS / WASM | — | — | 由 NOT 子句排除（不变） |

### 构建机实测（非推断）

在 pass 2 的构建目录上就地改条件并**重跑 configure**（复用 cache，因而不改变
任何其它 flag），对比 `link.txt`：

| | pass 2 `benchmark_filament` 的 `-lbluegl` | pass 1 host-tools 的 bluegl |
|---|---|---|
| 修复前 | 1 | `libs/bluegl`、`benchmark_filament`、`filamesh` 三处 link.txt 均含 |
| 修复后 | **0** | **完全不变** ✔ |

实验后已把源码还原并重新 configure，构建树恢复原状。补丁本身另经
`patch -p1 --dry-run`（rc=0）与实应用逐字节比对验证。

## 附录：combine 的幂等性缺口 —— scratch 目录跨轮累积，最终 ENAMETOOLONG

`c265b6fc85a5` 这一轮 pass 2 走到 **68%** 后失败：

```
mv: bad '/storage/Users/currentUser/tmp/_libfilamat_combined/libSPIRV-Tools-opt/
         libSPIRV-Tools-opt_libSPIRV-Tools-opt_…_eliminate_dead_output_stores_pass.cpp.obj'
make[2]: *** [libs/filamat/CMakeFiles/filamat.dir/build.make:487: libs/filamat/libfilamat.a] Error 1
```

**根因**：`temp_dir` 由**输出库名**派生（`${COMBINE_WORK_ROOT}/_${输出 basename}`），所以同一条
combine 每次跑都用**同一个目录**；而脚本对它只做 `mkdir -p`，从不清理。一轮**中途失败**会把已解出的
对象留在原地，下一轮的重命名循环便再叠一层 `dir_name_` 前缀。成员名较长的归档会率先撞上
`NAME_MAX`(255)，`mv` 随即以 ENAMETOOLONG 失败。

留档证据（`runtime/combine-scratch-evidence-*.txt`）：

| 项 | 实测 |
|---|---|
| 暂存目录 mtime | `2026-09-15 13:00:36`（**上一轮遗留**，非本次新建） |
| 文件总数 | 2448 |
| `libSPIRV-Tools-opt/` 内文件 | 1009，其中 **831 个带双重前缀** |
| 最长文件名 | **250 字符**（上限 255） |
| 前缀叠加层数 | 最多 **11 层**（`libspirv-cross-core_` 重复 11 次） |
| 受影响的 archive 子目录 | **10/10 全部** |

**修复**：在处理 archive 列表**之前**，对 `temp_dir` 执行一次清理：

```sh
case "${temp_dir}" in
    "${COMBINE_WORK_ROOT}"/_?*) rm -rf "${temp_dir}" ;;
    *) echo "$SELF_NAME: refusing to clean unexpected scratch '${temp_dir}'" >&2; exit 1 ;;
esac
mkdir -p "${temp_dir}"
```

之所以清理整轮（而不是每个 archive 各清各的）：最终组包是
`"${AR_TOOL}" -qc "${output_path}" $(object_files "${temp_dir}")`，靠 `find` 收集
**整个 temp_dir** 下的对象，因此各 archive 的对象必须**共存到最后一刻**；整轮清一次既清掉了上轮残留，
又不会误删本轮前面 archive 的对象。

**刻意不加**"文件名已带 `dir_name_` 前缀就跳过"的逻辑：实测 9 个真实输入归档中，
**没有任何一个成员名以 `dir_name_` 开头**（逐个 `ar t | grep -c "^${dir_name}_"` 均为 0），
所以一次全新解包不可能产生带前缀的名字——加那条规则只会掩盖 stale scratch，而不是根治。

### 回归证据（用真实 Filament 归档，9 个输入）

| 测试 | 结果 |
|---|---|
| T1 干净起点 | rc=0，`mv:bad=0`，members=**269**，maxlen=68 |
| T2 先播种 60 个"上轮残留"对象 | rc=0，members=**269**，双重前缀=0，残留泄漏=0，**与 T1 成员表完全一致** |
| T3 再播种并连跑两次 | rc=0，members=**269**，maxlen=68，**与 T1 一致** |
| T4 语义 | 269 个 `.obj` / 0 个 `.o`、重名 0、9 个归档的前缀分布完整保留 |
| **判别组**：同样播种、**旧脚本** | members=**329**（多 60）、maxlen=**83**、双重前缀=**60**、残留泄漏=**60**、与 T1 **不一致** |

即：旧脚本会把残留对象原样放进归档并二次加前缀；新脚本每次都产出同一个确定的 269 成员归档。

**0001 现在的覆盖范围**（其余补丁 0002 / 0003 与 C++23 fallback 均未改动）：

- cwd-independent extraction（绝对路径，`--output=DIR`，不再 `cd`/`pushd`）
- absolute extraction path
- `.o` / `.obj` 双扩展名支持
- duplicate member 通过 `dir_name_` 前缀保留
- **clean per-invocation scratch**
- **repeated invocation idempotency**

## 附录：包布局 —— 归档装进了 `lib/unknown/`，test_package 因此找不到静态库

`598198851c52` 这一轮 pass 2 已经走到 **100%**、`Package created: 1`，随后在 **test_package
的 configure** 阶段失败：

```
CMake Error at CMakeLists.txt:29 (message):
  no static archives found under
  /storage/.../p/b/filam8a533f0e002f4/p/lib
```

包确实建出来了，但 `lib/` 底下**一个 `.a` 都没有**：

| 位置 | 内容 |
|---|---|
| `p/lib/unknown/` | **34 个静态库**（`libfilament.a`、`libfilabridge.a`、…） |
| `p/lib/*.a` | **0** |
| `p/include/` | 正常 |

**根因**：Filament 的安装规则写的是

```cmake
install(TARGETS ... ARCHIVE DESTINATION lib/${DIST_DIR})     # 全树约 28 处
```

而 `DIST_DIR` 由 `DIST_ARCH` 推导（`CMakeLists.txt:735-757`），`DIST_ARCH` 未显式给定时回退到
`CMAKE_HOST_SYSTEM_PROCESSOR`。鸿蒙内核的 **`uname -p` 返回字面量 `unknown`**（`uname -m` 才返回
`aarch64`），于是每个归档都被装进 `lib/unknown/`。`include/` 不走 `DIST_DIR`，所以头文件是好的
——这也正好解释了为什么只有库目录出问题。

**这不只是 test_package 的毛病**：recipe 的 `package_info()` 只设了 `cpp_info.libs = ["filament"]`，
没设 `libdir`，而 Conan 的默认 `libdir` 就是 `lib`（实测 `dep.cpp_info.libdir` 返回绝对路径
`<pkg>/lib`）。也就是说**包的实际布局与它自己声明的 libdir 不一致**，任何经 CMakeDeps /
pkg_config 消费它的工程都会拿到一个指向空目录的 `-L`。

**修复**（保留上游的布局形状，只把架构名改对）：

1. recipe 新增模块常量 `DIST_ARCH = "aarch64"`，在 `generate()` 里
   `tc.variables["DIST_ARCH"] = DIST_ARCH`。两个 pass 共用同一个 `generate()`，且 pass 1 也通过
   `-DCMAKE_TOOLCHAIN_FILE` 读同一份 toolchain，故两边目录名一致。实测 `DIST_ARCH` 全树唯一的另一处
   用途在 `if (IOS)` 分支内（`CMakeLists.txt:891`），鸿蒙上是死代码，覆盖安全。
2. `package_info()` 设 `self.cpp_info.libdir = f"lib/{DIST_ARCH}"`，让声明与实际一致。
3. `package()` 增加断言：安装完成后 `lib/<DIST_ARCH>/` 下必须存在 `.a`，否则直接抛
   `ConanException`。同类问题将来会在**打包阶段**带着清楚的原因失败，而不是拖到消费者的 configure。
4. test_package 不再硬编码 `${FILAMENT_PKG_DIR}/lib`，改为从
   `self.dependencies["filament"].cpp_info.libdir` 取值传给 CMake。这同时把那次 configure 变成一次
   真实的断言：**包的布局 == 声明的 libdir**。

**刻意没有**把安装目标改成 `lib/`：上游在正常 Linux 主机上 `uname -p` 返回真实架构（如 `x86_64`），本来
就装到 `lib/<arch>/`；`lib/unknown` 只是架构名错了，布局形状本身是上游设计。改架构名比改 28 处
`install()` 更小、更贴近上游，也不与 `DIST_DIR` 的既有语义打架。

## 更正：`cpp_info.libdir` 是只读 property，必须用 `libdirs`（复数、list）

上一节写的

```python
self.cpp_info.libdir = f"lib/{DIST_ARCH}"     # 错，会在 package_info() 里直接抛异常
```

是**错的**，这里更正。

**Conan 2.29.1 的 CppInfo**（`site-packages/conan/internal/model/cpp_info.py`）：

```python
    @property
    def libdir(self):                     # :239  —— 只有 getter
        libdirs = self.libdirs
        if not libdirs or len(libdirs) != 1:
            raise ConanException(...)     # :243  —— 还要求列表恰好一个元素
        return libdirs[0]
```

同文件里 `libdirs` 有 `@libdirs.setter`（:196），`bindirs`（:217）、`includedirs`（:177）也都有 setter，
**唯独 `libdir` 没有**。所以对单数赋值不是"静默无效"，而是**硬失败**：`package_info()` 抛
`AttributeError`，`conan create` 以 rc=1 结束。

**最小实验**（隔离 `CONAN_HOME`，不碰农场 cache）：

| 变体 | 结果 |
|---|---|
| `self.cpp_info.libdir = "lib/aarch64"` | `ERROR: Error in package_info() method, line 12` / **rc=1** |
| `self.cpp_info.libdirs = ["lib/aarch64"]` | `Package created` / **rc=0** |

**真实 recipe 验证**（不需要编译：把本 recipe 的 `package_info` 函数对象原样绑到一个探针类上，
`package()` 只 fabricate 出 `lib/aarch64/*.a`，再用 CMakeDeps 消费）：

```
Q4  cpp_info.libdirs = ['<pkg>/lib/aarch64']
Q5  filament-release-armv8-data.cmake:27
      set(filament_LIB_DIRS_RELEASE "${filament_PACKAGE_FOLDER_RELEASE}/lib/aarch64")
    unknown 出现次数：所有生成文件均为 0
    add_library(filament::filament INTERFACE IMPORTED)
```

**正确写法**：

```python
def package_info(self):
    self.cpp_info.libs = ["filament"]
    self.cpp_info.libdirs = [f"lib/{DIST_ARCH}"]     # 复数、list、相对 package root
```

consumer 侧读同一个复数形式：

```python
dep.cpp_info.libdirs[0]        # 不读单数：它在元素数 != 1 时会抛异常
```

**教训**：`libdir` 能被**读**（包只有一个 libdir 时 getter 正常工作）不代表能被**写**。
验证一个字段是不是官方可写字段，必须查 setter / 做赋值实验，不能因为读得到就推断写得进。

## 附录：test_package 的两个独立问题（`TEST_BUILD_ERROR` + `TEST_RUNTIME_ERROR`）

`684648e319d5` 这轮 **pass 2 跑到 100%、package 成功、test_package configure 通过**——
`lib/aarch64/` 下 34 个 `.a`、`lib/unknown/` 为 0，前面所有修复都成立。随后连续撞上两个
**新的、互相独立**的问题。

### 一、`TEST_BUILD_ERROR`：`test_filament.cpp` 用了不存在的 API

```
test_filament.cpp:53:11: error: use of undeclared identifier 'Backend'; did you mean 'backend'?
    check(Backend::NOOP == static_cast<Backend>(5),
```

两个根因，都只在**我们自己的**测试文件里（唯一失败的编译单元）：

1. **命名空间**：`Backend` 声明在 `filament::backend`（`backend/DriverEnums.h:175`），而文件里只写了
   `using namespace filament;`。修法是加一行**别名**（而非再开一个 using-directive，保持显式）：

   ```cpp
   using Backend = filament::backend::Backend;
   ```

   `NOOP = 5` 与测试里的 `static_cast<Backend>(5)` 一致，无需改动。

2. **Camera 的销毁 API**：`Engine.h` 里**根本没有** `destroy(Camera*)` 重载
   （992–1021 行覆盖 BufferObject / VertexBuffer / Fence / Sync / IndexBuffer / SkinningBuffer /
   MorphTargetBuffer / IndirectLight / Material / MaterialInstance / Renderer / FramePacer / Scene /
   Skybox / ColorGrading / SwapChain / Stream / Texture / RenderTarget / View / InstanceBuffer，
   不含 Camera）。权威答案在被装头文件里 —— `Camera.h:53-54`：

   > A Camera component is destroyed using `Engine::destroyCameraComponent(Entity)`.

   于是 `engine->destroy(camera)` 改为 `engine->destroyCameraComponent(cameraEntity)`。

**最小验证**（复用设备上已存在的 test_package 构建目录，只重编这一个单元 + 链接）：

```
[ 50%] Building CXX object CMakeFiles/test_filament.dir/test_filament.cpp.obj
[100%] Linking CXX executable test_filament
[100%] Built target test_filament      rc=0
```

### 二、`TEST_RUNTIME_ERROR`：材质只有 MOBILE 着色器，而所有驱动都报 DESKTOP

链接成功后运行：

```
    ok   : Backend::NOOP enum value present
The material 'Filament Default Material' was not built for desktop.
Compiled material contains shader models 0x2.
timeout: the monitored command dumped core        (exit 139)
```

**根因链**：

- 运行期：`MaterialDefinition.cpp:257-272` 取引擎的 `ShaderModel` 与材质的位掩码比对，
  不匹配就 `return nullptr`，随后 `Engine::create` 在空指针上崩溃。
  位掩码 `0x2` = bit1 = **MOBILE**（`DriverEnums.h:655-658`：`MOBILE=1, DESKTOP=2`）。
- **该设备上每一个驱动都返回 `ShaderModel::DESKTOP`**：`NoopDriver.cpp:50`、
  `VulkanDriver.cpp:441`、`OpenGLContext.cpp:117`、`WebGPUDriver.cpp:143`、`MetalDriver.mm:1262`。
- 构建期：`MATC_TARGET` 由 `IS_MOBILE_TARGET` 决定（`CMakeLists.txt:697-702`），而
  `IS_MOBILE_TARGET` 由 `FILAMENT_LINUX_IS_MOBILE` 置位（`:247`）→ `MATC_TARGET mobile`
  → 内嵌材质**只有 MOBILE 变体**。
- 而 `FILAMENT_LINUX_IS_MOBILE=ON` **是承重的**：补丁 0002 用 `IS_HOST_PLATFORM` 作 bluegl 的
  排除条件，而 `IS_HOST_PLATFORM` 恰恰在 `FILAMENT_LINUX_IS_MOBILE` 为 OFF 时才置位（`:258`）。
  所以不能关掉它。

**修复**：让 matc 同时产出两个着色器族，而不去动那个承重开关。

`CMakeLists.txt:729` 是

```cmake
set(MATC_BASE_FLAGS ${MATC_API_FLAGS} -p ${MATC_TARGET} ${MATC_OPT_FLAGS})
```

而 `MATC_OPT_FLAGS` 全程**只被追加**（`:721`、`:726`），从不从零 `set`，所以从 Conan toolchain 传值
会落在 `-p mobile` **之后**。matc 对重复 `-p` 是**赋值**而非按位或（`CommandlineConfig.cpp:320-324`），
因此**最后一个生效**：

```python
tc.variables["MATC_OPT_FLAGS"] = "-p all"
```

`Platform::ALL` 会同时置两个 shader model（`MaterialBuilder.cpp:125-126`）。

**验证（三层，都不需要重新编译整包）**：

1. **CMake 管道** —— 用最小工程原样复刻 `:704-729`：

   ```
   without: MATC_BASE_FLAGS = [-a;opengl;-a;vulkan;-p;mobile]
   with   : MATC_BASE_FLAGS = [-a;opengl;-a;vulkan;-p;mobile;-p all]
   ```

2. **matc 产物** —— 用已构建的 matc 编同一个默认材质：

   | `-p` | rc | 产物字节 |
   |---|---|---|
   | mobile | 0 | 49,345 |
   | desktop | 0 | 45,422 |
   | **all** | **0** | **83,913** |

   即 `all` 同时含两个着色器族，运行时 `test(DESKTOP)` 得以通过。

3. **源码链** —— `Platform::ALL` → `mShaderModels.set(MOBILE); mShaderModels.set(DESKTOP);`。

**没有**采取的两条路：关掉 `FILAMENT_LINUX_IS_MOBILE`（会破坏 0002 的 bluegl 排除），
以及新增补丁去改 `MATC_TARGET`（toolchain 变量已足够，不必再动源码）。

## 更正：`MATC_OPT_FLAGS = "-p all"` 是我的回归，必须写成 `"-p;all"`

上一节的修复**方向正确但写法有 bug**，在 `830df5382b62` 那轮 pass 1 的 66% 处炸掉：

```
[ 66%] Built target matc
[ 66%] Compiling material .../filament/src/materials/antiAliasing/taa/taa.mat
Unrecognized platform. Must be 'desktop'|'mobile'|'all'.
Invalid parameters.
make[3]: *** [...: filament/generated/material/taa.filamat] Error 1
```

**根因**：`MATC_BASE_FLAGS` 是 CMake **list**，最终经 `add_custom_command` 生成命令行。我传的
`-DMATC_OPT_FLAGS="-p all"` 含空格，在 list 里是**单个元素**，生成时被加引号 → matc 收到的
`argv` 是**一个** `-p all` 字符串；getopt 的 `-p` 要求参数，于是把整串 `-p all` 当成了平台名，
自然无法识别。

**用一个打印 argv 的假 matc 精确复现并验证**（`fake-matc` 逐行打印 `$@`，工程原样复刻
`CMakeLists.txt:704-729` 并走 `add_custom_command`）：

| 写法 | matc 实际收到的 argv |
|---|---|
| `"-p all"` | `argv[5]=[-p]  argv[6]=[mobile]  argv[7]=[-p all]` ← 单个参数，故障 |
| `"-p;all"` | `argv[5]=[-p]  argv[6]=[mobile]  argv[7]=[-p]  argv[8]=[all]` ← 两个参数，正确 |

**修法**：CMake 中 `;` 是 list 分隔符，因此

```python
tc.variables["MATC_OPT_FLAGS"] = "-p;all"
```

展开后成为两个独立元素，matc 依 `CommandlineConfig.cpp:320-324` 的赋值语义取最后一个 →
`Platform::ALL` → 同时产出 MOBILE + DESKTOP。

**为什么 `-p all` 在两边都安全**：pass 1 用 `-p desktop`、pass 2 用 `-p mobile`，也就是说
**两个着色器族本来就各自编译成功过**（只是分处两个 pass）。`all` 只是把它们放进同一次
matc 调用，不会引入新的着色器编译失败。

## 更正：`__OHOS__` 已全部移除，两处补丁改为「能力」而非「平台身份」

前文（§0002 一节）描述的 `defined(__OHOS__)` 写法**已废弃**。审查按项目 R8 规则
（"源码和 patches/ 补丁不得引入平台条件编译宏"）判为 request-changes 级风险，本次一并去平台化。

### 0002 —— `gl_headers.h`

不再判断平台，改由 CMake 在**"本次构建不链接 bluegl"的同一条件**下注入能力宏：

```cmake
if(FILAMENT_SUPPORTS_OPENGL AND NOT IOS AND NOT ANDROID AND NOT WASM AND IS_HOST_PLATFORM)
    target_link_libraries(${TARGET} PRIVATE bluegl)
elseif(FILAMENT_SUPPORTS_OPENGL AND NOT IOS AND NOT ANDROID AND NOT WASM)
    # bluegl is not part of this build, so the GL sources must take the system
    # GLES3 headers.  Expressed as a build capability rather than a platform identity.
    target_compile_definitions(${TARGET} PRIVATE FILAMENT_GLES3_FROM_SYSTEM)
endif()
```
```c
#if defined(__ANDROID__) || defined(FILAMENT_GLES3_FROM_SYSTEM) || defined(FILAMENT_USE_EXTERNAL_GLES3) || ...
```

**刻意不用** `FILAMENT_USE_EXTERNAL_GLES3`：实测它会**整块剔除 OpenGL/GLES 源码**
（`backend/CMakeLists.txt:85`）并让 `PlatformFactory.cpp:166` 对 OPENGL 后端返回 nullptr——那是功能变更。
主机趟（pass 1）`IS_HOST_PLATFORM` 为真，依旧链接 bluegl，行为不变。

### 0003 —— `perfetto.cc`

不再判断平台，改为**配置期能力探测**：

```cmake
include(CheckCXXSourceCompiles)
check_cxx_source_compiles("#include <sys/socket.h>\n#include <linux/vm_sockets.h>\nint main(){return 0;}"
                          FILAMENT_SYSTEM_VM_SOCKETS_USABLE)
if(NOT FILAMENT_SYSTEM_VM_SOCKETS_USABLE)
    target_compile_definitions(${TARGET} PRIVATE FILAMENT_NO_SYSTEM_VM_SOCKETS)
endif()
```
```c
#elif defined(AF_VSOCK) && !defined(FILAMENT_NO_SYSTEM_VM_SOCKETS)
```

**实测（本机三组对照）**：受测片段在本 sysroot **失败**（正是 `redefinition of sockaddr_storage`），
正控片段 **成功并返回 `1`**——即"失败得空值 / 成功得 1"，`if(NOT ...)` 是可靠判据。
正常 Linux 主机上探测通过、宏不注入，**上游行为不变**。

### 0001 —— 顺带修一个静默失效

审查发现 `object_files()` 不转发多余参数，于是 `object_files "$dir" -delete` 里的
`-delete` **被吞掉**，归档后的清理从未发生。已修为：

```sh
object_files() {
    local dir="$1"
    shift
    find "$dir" -type f \( -name '*.o' -o -name '*.obj' \) "$@"
}
```
**实测对照**（3 个临时对象）：新写法 `before=3 → after=0`，`rc=0`；旧写法 `before=3 → after=3`。
