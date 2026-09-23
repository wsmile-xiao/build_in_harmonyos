# phonon4qt6 4.12.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-14
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

phonon4qt6 4.12.0 是 KDE Multimedia Qt6 多媒体框架，CMake 构建，产出
`libphonon4qt6.so`（SOVERSION 库，纯库类型，无需 commands.json）。

```bash
# 1. W0 依赖检查（R35 用 conan download 验证）
conan download ecm/6.20.0 -r=ohpcd --only-recipe
conan download qtbase/6.11.1 -r=ohpcd --only-recipe
conan download qt5compat/6.11.1 -r=ohpcd --only-recipe
conan download qttools/6.11.1 -r=ohpcd --only-recipe

# 2. init-build（官方源已验证）
ohc-run.py init-build phonon4qt6 4.12.0 \
  --url=https://download.kde.org/stable/phonon/4.12.0/phonon-4.12.0.tar.xz

# 3. lang-preflight（R47）→ cpp 匹配

# 4. 探索编译
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -DPHONON_BUILD_QT5=OFF -DPHONON_BUILD_QT6=ON \
  -DPHONON_BUILD_DESIGNER_PLUGIN=OFF \
  -DPHONON_BUILD_DEMOS=OFF -DPHONON_BUILD_DOC=OFF \
  -DPHONON_BUILD_SETTINGS=OFF -DPHONON_BUILD_EXPERIMENTAL=OFF \
  -DECM_DIR=<ecm>/share/ECM/cmake \
  -DQT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qttools>/lib/cmake \
  -DCMAKE_PREFIX_PATH="<qtbase>/lib/cmake;<qt5compat>/lib/cmake;<qttools>/lib/cmake" \
  -DCMAKE_MODULE_PATH="<ecm>/share/ECM/{cmake,modules,find-modules,kde-modules}" \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -jN && make install DESTDIR=$TEST_PREFIX
# make check → 无目标（上游无测试，R51 清点）

# 5. conan-init → 手工改写为 CMake 配方（init 误判 autotools）
# 6. conan-verify → 8 道门禁全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 失败: `add_library cannot create ALIAS target Qt::OpenGLWidgets` | qtbase OHOS 包未编译 OpenGL（FEATURE_opengl 关闭），`Qt6::OpenGLWidgets` 目标不存在，上游 CMakeLists 无条件创建 ALIAS | 补丁 0001 将 ALIAS 创建包在 `if(TARGET Qt6::OpenGLWidgets)` 中（通用健壮性修复，非平台宏） |
| 2 | configure 失败: Qt6LinguistTools 找不到 | qtbase 的 Qt6Config 组件查找只搜 `_qt_cmake_dir`（qtbase 自身），qttools 的 LinguistTools 模块未被发现；ECMPoQmTools 翻译生成需要 | 配方 generate() 设置 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qttools>/lib/cmake` |
| 3 | conan create 构建期 lconvert 运行报 symbol not found | 宿主工具（lconvert/qtpaths）运行时 LD_LIBRARY_PATH 未包含 qtbase 等依赖库 | build() 中遍历 `self.dependencies` 将每个依赖的 `lib/` prepend 进 LD_LIBRARY_PATH（karchive 先例），OHOS 下再 prepend `/system/lib64` |
| 4 | test_package ctest 运行失败: Error loading shared library libQt6Core.so.6 | test() 内手动 `env.vars(self).apply()` 包裹 ctest 时环境注入不生效/不完整 | 改按 karchive 先例：`self.run('ctest ...', env="conanrun")` 使用 Conan 生成的 VirtualRunEnv |
| 5 | init-build/conan-init 误判构建系统为 autotools | init 脚本按 configure 脚本存在性猜测；本项目无 configure（纯 CMake） | 手工改写 conanfile.py 为 CMakeToolchain 版本；lang-preflight 正确识别 cmake |
| 6 | W3 L5 SONAME 门禁 FAIL（3 errors）：libphonon4qt6.so 无 DT_SONAME、DT_NEEDED 含 conan 缓存绝对路径、cmake 文件 IMPORTED_NO_SONAME TRUE | ①OHOS 适配版 conan 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 4.1 无 Platform/HarmonyOS.cmake → Linux 平台模块未加载 → SONAME flag 缺失；②qt5compat 的 libQt6Core5Compat.so 无 SONAME → 链接时记录绝对路径（E537） | ①generate() 注入 CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG="-Wl,-soname," + CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME=1；②按 E537 方案 cmake_language(DEFER) 为 Qt6::Core5Compat 重设 IMPORTED_SONAME=libQt6Core5Compat.so 并清 IMPORTED_NO_SONAME |

## 源码修改

patches/0001-guard-openglwidgets-alias.patch — CMakeLists.txt 中
`add_library(Qt::OpenGLWidgets ALIAS Qt6::OpenGLWidgets)` 增加
`if(TARGET Qt6::OpenGLWidgets)` 守卫（qtbase OHOS 无 OpenGLWidgets 组件）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| qtbase | 6.11.1 | Qt6Core/Gui/Widgets |
| qt5compat | 6.11.1 | Qt6Core5Compat (REQUIRED) |
| qttools | 6.11.1 | Qt6LinguistTools（ECMPoQmTools 翻译生成） |
| ecm | 6.20.0 | Extra CMake Modules（tool_requires） |

可选未用：ALSA（Linux 音频）、PulseAudio/GLIB2（RECOMMENDED 且 OHOS 不相关，configure 自动跳过）、
Qt6Designer（qttools 未导出该 cmake 模块，Designer 插件禁用）、Qt6OpenGLWidgets（qtbase OHOS 无此组件）。

## 验证结果

- conan-verify 8 道门禁全 PASS（G0-G4 + L2/L4/L5）
- test_package：链接 Phonon::phonon4qt6，调用 Phonon::phononVersion() /
  BackendCapabilities::availableMimeTypes() / availableAudioOutputDevices()，
  conanrun 环境下运行 PASS（"Phonon version: 4.12.0"，backend=0 属预期——
  OHOS 无后端插件，但库本身可加载可链接）
- 上游测试（R51 清点）：phonon-4.12.0 源码树无 tests/ 目录、无 ctest 注册、
  无独立测试程序 → 上游测试数为 0

## 注意事项

- QT_ADDITIONAL_PACKAGES_PREFIX_PATH 是 Qt6Config 组件查找的关键变量：
  不带它则 find_package(Qt6 COMPONENTS LinguistTools) 失败
- build() 的 LD_LIBRARY_PATH 注入对宿主工具（lconvert）运行必不可少
- 产物纯库（无 bin/），R38 无需 commands.json
---

**编译结束**: 2026-09-15 02:09
**最终状态**: published
