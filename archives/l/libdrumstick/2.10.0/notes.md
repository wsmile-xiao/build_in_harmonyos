# libdrumstick 2.10.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-17
- 编译器: clang/clang++ (clang 15.0.4, -stdlib=libc++)
- 状态: built

## 编译步骤

```bash
# 依赖注入（conan install 生成 CMakeDeps + CMakeToolchain）
conan install --requires=qtbase/6.11.1 --requires=qt5compat/6.11.1 \
    --requires=qttools/6.11.1 --requires=fluidsynth/2.5.7 \
    -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -g CMakeDeps -g CMakeToolchain

# CMake 配置（关键：CMAKE_SYSTEM_NAME=OHOS）
cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
    -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH=<qtbase>;<qt5compat>;<qttools>;<fluidsynth> \
    -DQt6Core5Compat_DIR=<qt5compat>/lib/cmake/Qt6Core5Compat \
    -DQt6LinguistTools_DIR=<qttools>/lib/cmake/Qt6LinguistTools \
    -DBUILD_ALSA=OFF -DUSE_SONIVOX=OFF -DUSE_PULSEAUDIO=OFF -DUSE_PIPEWIRE=OFF \
    -DUSE_FLUIDSYNTH=ON -DUSE_NETWORK=ON -DBUILD_DOCS=OFF -DBUILD_TESTING=ON

make -j2 && ctest --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 "System is unknown to cmake, create: Platform/HarmonyOS" | OHOS conan toolchain 把系统映射为 HarmonyOS，但 CMake 4.1 无 Platform/HarmonyOS.cmake（只有 OHOS.cmake） | `-DCMAKE_SYSTEM_NAME=OHOS`，让 CMake 加载 Platform/OHOS.cmake（include Linux） |
| 2 | 库无 SONAME；rtTest 报 "There aren't input backends" | 平台未识别导致共享库不生成 SONAME，RT 插件 DT_NEEDED 写成相对路径 `../../../lib/libdrumstick-rt.so`，运行时从 lib/drumstick2/ 解析错位 | 同问题 1：设 CMAKE_SYSTEM_NAME=OHOS 后库生成 `libdrumstick-rt.so.2` SONAME，插件 DT_NEEDED 用 SONAME，ctest 5/5 通过 |
| 3 | cmake 运行时 "Error loading shared library libc++_shared.so" | moc/lrelease 等 Qt 工具运行期需要 libc++_shared.so（在 OHOS SDK llvm lib 目录） | LD_LIBRARY_PATH 追加 SDK `llvm/lib/aarch64-linux-ohos(/c++)` 与 qtbase lib 目录 |
| 4 | fluidsynth.pc 的 prefix 指向已清理的 build 目录（`p/b/fluid...`） | fluidsynth 包发布的 .pc 未按 package_folder 重写 prefix | build 私有 prefix 下重写 `prefix=<fluidsynth package_folder>`，经 PKG_CONFIG_PATH 注入（R49） |
| 5 | Qt6Core5Compat/ListinguistTools 找不到 | qtbase 使用 cmake_find_mode=none，CMakeDeps 不为其生成配置 | 显式 CMAKE_PREFIX_PATH + Qt6Core5Compat_DIR + Qt6LinguistTools_DIR |

## 源码修改

无源码补丁（patches/ 为空）。全部适配在 conanfile.py 层完成。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1 | Qt6Core/Network/Gui/Widgets/Xml/Test |
| qt5compat | 6.11.1 | Qt6Core5Compat（BUILD_FILE 需要） |
| qttools | 6.11.1 | Qt6LinguistTools/Qt6UiPlugin（widgets/vpiano-plugin 需要） |
| fluidsynth | 2.5.7 | FluidSynth RT 后端 |

关闭的可选依赖：ALSA(BUILD_ALSA)、Sonivox(USE_SONIVOX)、PulseAudio(USE_PULSEAUDIO)、PipeWire(USE_PIPEWIRE)——OHOS 制品仓无对应包/无 ALSA sequencer。

## 验证结果

```bash
$ ctest --output-on-failure -j1
100% tests passed, 0 tests failed out of 5
# fileTest1 fileTest2 fileTest3 rtTest widgetsTest 全部通过

# 安装产物
lib/libdrumstick-file.so.2.10.0 / libdrumstick-rt.so.2.10.0 / libdrumstick-widgets.so.2.10.0
lib/drumstick2/libdrumstick-rt-{fluidsynth,net-in,net-out,oss-in,oss-out}.so
bin/drumstick-{dumprmi,dumpsmf,dumpwrk,vpiano}
include/drumstick/*.h   lib/pkgconfig/drumstick-{file,rt,widgets}.pc
```

## 注意事项

- 上游测试共注册 5 项（alsaTest1/alsaTest2 依赖 ALSA sequencer 仅 Linux，OHOS 上 BUILD_ALSA=OFF 不注册）。
- Qt 运行期库路径（qtbase lib + SDK libc++）需在 build 与 test 时注入 LD_LIBRARY_PATH。
- 本适配为 Qt6 路线；Qt5 包缺 LinguistTools/UiPlugin 组件，不可用。
---

**编译结束**: 2026-09-17 12:47
**最终状态**: built
