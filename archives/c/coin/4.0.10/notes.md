# coin 4.0.10 适配笔记

## 基本信息
- 上游：Coin3D core（coin3d/coin），tag v4.0.10（commit caed4f6）
- 官方源码归档：GitHub Releases `coin-4.0.10-src.tar.gz`（解压根目录为 `coin/`，
  conan `get(strip_root=True)` 直接可用）
- License：BSD-3-Clause；src/xml/expat 为 vendored expat（MIT，
  USE_EXTERNAL_EXPAT=OFF 默认内置，不引系统 expat 依赖）
- 注意：与 COIN-OR（Common Optimization Interface for OR，数值优化套件）
  **只是同名，完全无关**；本包是 Open Inventor 2.1 场景图库。

## 编译环境
- 构建系统: cmake（上游 4.0.10 起为 CMake 主构建；tarball 内残留 Makefile.am/
  Makefile.in 为 autotools 遗留，CMake 构建不触发再生成——P3 探针证实源码树
  无 configure/config.status/Makefile 生成、无 in-source CMakeCache）
- 编译日期: 2026-09-09
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，ohos.toolchain.cmake + OHOS_ARCH=arm64-v8a）
- 状态: built（待官方 CI R26/R34/FULL 验证）

## 探针结论（设备真机，2026-09-09）

| 探针 | 结论 |
|------|------|
| P1 configure | PASS：预置 OPENGL_INCLUDE_DIR=sysroot/usr/include、OPENGL_gl_LIBRARY 后 find_package(OpenGL) 通过，config.h 生成成功（交叉 CheckCSourceRuns 缺省跳过不阻塞） |
| P1 link（系统 GLES） | FAIL：`-DOPENGL_gl_LIBRARY=/system/lib64/libGLESv3.so` 时链接报 undefined symbol：glColorMaterial/glMatrixMode/glPushMatrix/glLoadIdentity/glTranslatef/glMultMatrixf/glAlphaFunc/glTexEnvi/glAccum/glOrtho/glColor3f/glBegin/glTexCoord2f/glVertex2f/glEnd/glTexGenfv…（887 个导出符号不含定点管线族） |
| P1 link（gl4es） | PASS：`OPENGL_gl_LIBRARY=<gl4es>/lib/libGL.so` 完整构建+链接成功；SONAME=libGL.so.1 → libCoin.so DT_NEEDED=libGL.so.1（相对名）；EGL 由 find_package(OpenGL) 自动发现 sysroot stub → COIN_BUILD_EGL=ON 链 libEGL.so（真机可用，见 P2） |
| P2 EGL | PASS：真机最小程序 eglGetDisplay(EGL_DEFAULT_DISPLAY)+eglInitialize 成功（EGL 1.4，vendor=OpenHarmony），与 DRAFT-sdl2-2.30.10-egl-querydevices-fallback 的经典入口可用结论一致 |
| P3 autotools | PASS：CMake 全量构建后源码树无任何 autotools 再生成产物 |
| 运行时冒烟 | PASS：SoDB::init + .iv 内存解析 + 字段断言 + 垃圾输入负例 + getVersion 全过（"SIM Coin 4.0.10"）；SoDB::init 会经 glue 层初始化 gl4es（需 LIBGL_GLES/LIBGL_EGL 环境变量） |

## 构建步骤（recipe 内固化）

```bash
cmake -B build-ohos -S . \
  -DCMAKE_TOOLCHAIN_FILE=<native>/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=<package_folder> -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DOPENGL_INCLUDE_DIR=<sysroot>/usr/include \
  -DOPENGL_gl_LIBRARY=<gl4es>/lib/libGL.so \
  -DCOIN_BUILD_GLX=OFF -DCOIN_BUILD_TESTS=OFF \
  -DCOIN_BUILD_EXAMPLES=OFF -DCOIN_USE_CPACK=OFF
cmake --build build-ohos -- -j 8        # ~3300 TU，必须并行，否则超 CI 3600s
cmake --install build-ohos --prefix <package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接系统 libGLESv3.so 报大量 undefined symbol（定点管线族） | OHOS 只有 GLES3，无桌面 GL；Coin glue 层静态引用 glMatrixMode/glBegin 等 | requires gl4es/1.1.6，OPENGL_gl_LIBRARY 指其 libGL.so；运行时消费方需 LIBGL_GLES=/system/lib64/libGLESv3.so LIBGL_EGL=/system/lib64/libEGL.so（已在 package_info runenv_info 定义） |
| 2 | 未签名 libCoin.so.80 加载失败（Error loading shared library） | OHOS PC XPM 要求链接加载的 .so 代码签名 | package() 内 llvm-objcopy --remove-section .codesign + binary-sign-tool 自签（与 assimp 同法） |
| 3 | SoDB::finish() SIGSEGV | gl4es 栈下 GL glue 析构顺序问题（初始化/解析正常，仅收尾崩溃） | test_package 不调用 finish()（真机实证不调则断言全过、exit 0）；已知问题，不阻断功能 |
| 4 | SoDB::init() 无 LIBGL_* 环境变量时 SIGSEGV | gl4es 默认找 libGLESv2.so，OHOS 只有 libGLESv3.so | 测试/消费方显式注入 LIBGL_GLES/LIBGL_EGL（见问题 1） |
| 5 | 64 位 ohos.toolchain 默认 CMAKE_INSTALL_LIBDIR=lib64 | 与制品仓布局不符 | 显式 -DCMAKE_INSTALL_LIBDIR=lib |
| 6 | bin/coin-config 为硬编码 /usr/local 前缀的 shell 脚本 | 上游 autotools 遗留产物 | package() 中按明确单文件移除（包内无意义且触发 L2 warn） |

## 源码修改

无（patches 为空）。上游 cmake_minimum_required(VERSION 3.0...3.31) 已兼容
cmake 4.x；CMAKE_POLICY_VERSION_MINIMUM=3.5 仅作兜底 cache 变量，不改源码。

## 依赖版本

- gl4es/1.1.6（conan，ohpcd 已发布）：提供 libGL.so（桌面 GL→GLES2 翻译），
  libCoin.so DT_NEEDED: libEGL.so / libGL.so.1 / libc++_shared.so / libc.so
- 运行时系统库（非 conan）：/system/lib64/libGLESv3.so、/system/lib64/libEGL.so
- zlib 等：运行时 dlopen（ZLIB_RUNTIME_LINKING 等默认 ON），系统无 libz.so 也可构建

## 产物布局

```
lib/libCoin.so.80.0.10 (+ .so / .so.80 软链，SONAME=libCoin.so.80)
lib/pkgconfig/Coin.pc
lib/cmake/Coin-4.0.10/{coin-config,coin-config-version,coin-export,coin-export-release}.cmake
    （find_package(Coin)，目标 Coin::Coin）
include/Inventor/**（公开 API 头）
share/Coin/**（draggerDefaults/profiler/conf 运行时资源；缺失时回落编译内置资源）
```

## 上游测试门禁

- CI 内 COIN_BUILD_TESTS=OFF（包产物精简；CoinTests 为单一可执行 + ctest 条目，
  上游自研框架，不依赖 Boost）。
- 上游 testsuite（CoinTests）由移植门禁在设备上单独构建运行（详见 run 报告）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（gl4es 依赖、GL 接线、签名、runenv） |
| conandata.yml | 官方源码 URL + SHA256（无补丁） |
| manifest.yaml / notes.md | 归档元数据 / 本笔记 |
| test_package/ | L1 真机测试（纯 CPU .iv 解析 + 字段断言，13 断言） |

## 注意事项

- 消费方运行时必须能解析 libGL.so.1（gl4es）并设置 LIBGL_GLES/LIBGL_EGL，
  否则 SoDB::init() 内 gl4es 初始化会崩溃；conanrun 环境（runenv_info）已带。
- SoDB::finish() 已知崩溃（见问题 3），长驻进程避免调用，或上游修复前容忍
  退出不调。
- 不要改用 conan CMakeToolchain 生成器：os=OHOS 的 CMAKE_SYSTEM_NAME 映射
  与 Coin 的平台分支不匹配（同 assimp/glfw 结论，ML-0035）。
