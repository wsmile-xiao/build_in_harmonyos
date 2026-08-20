# ArtyFX 1.3.1 适配笔记

## 软件信息
- 名称: artyfx
- 版本: 1.3.1
- 上游: https://github.com/openAVproductions/openAV-ArtyFX
- 构建系统: CMake
- 语言: C++
- License: GPL-2.0
- 描述: LV2 音频插件包（音频效果器集合）

## 依赖
- LV2 >= 1.8.0 (Conan: lv2/1.18.11-git) ✅ 已发布
- libsndfile (Conan: libsndfile/1.2.2) ⚠️ 制品仓未找到，设为可选
- Cairo (Conan: cairo/1.18.4) ✅ 已发布
- X11 ⚠️ OHOS 不可用，禁用 GUI
- AVTK (bundled in src/avtk/) - 随项目编译
- pthread (系统库)

## 编译步骤

### 1. init-build
```
python3 scripts/ohc-run.py init-build artyfx 1.3.1 --url=https://api.github.com/repos/openAVproductions/openAV-ArtyFX/tarball/release-1.3.1
```

### 2. 安装 Conan 依赖
使用 conanfile.txt 安装 lv2 和 cairo:
```
conan install . -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

### 3. 源码修改

#### 3.1 CMakeLists.txt
- 将 `pkg_check_modules(SND sndfile REQUIRED)` 改为可选 (`pkg_check_modules(SND sndfile)`)
- 添加 `HAVE_SNDFILE` 编译定义（仅当找到 sndfile 时）
- 条件链接 sndfile 库

#### 3.2 src/dsp/capta.cxx
- `#include <sndfile.hh>` 用 `#ifdef HAVE_SNDFILE` 保护
- diskFunc() 中的 sndfile 操作用 `#ifdef HAVE_SNDFILE` 保护
- 录音功能在无 sndfile 时优雅降级

#### 3.3 src/dsp/capta.hxx
- `class SndfileHandle;` 前向声明用 `#ifdef HAVE_SNDFILE` 保护
- `SndfileHandle* sndfile` 成员用 `#ifdef HAVE_SNDFILE` 保护

### 4. LV2 头文件路径兼容
LV2 1.18.11-git 使用新路径结构 (`lv2/core/lv2.h`)，而 ArtyFX 代码使用旧路径 (`lv2/lv2plug.in/ns/lv2core/lv2.h`)。
在 LV2 包的 include 目录创建兼容性符号链接:
- `lv2/lv2plug.in/ns/lv2core` → `../../core`
- `lv2/lv2plug.in/ns/ext` → `../..`
- `lv2/lv2plug.in/ns/extensions/ui` → `../../../ui`

### 5. CMake 配置
```
cmake .. \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_SSE=OFF \
  -DBUILD_GUI=OFF \
  -DBUILD_BENCH=OFF \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64
```

关键选项:
- BUILD_SSE=OFF: arm64 不支持 SSE 指令集
- BUILD_GUI=OFF: X11 在 OHOS 上不可用
- CMAKE_SYSTEM_NAME=Linux: cmake 不识别 HarmonyOS，设为 Linux 兼容

### 6. 编译和安装
```
make -j1
make install DESTDIR=$TEST_PREFIX
```

### 7. 产物
- artyfx.so (ELF 64-bit LSB arm64 shared object)
- 安装路径: lib/lv2/artyfx.lv2/
- 包含: artyfx.so + 15 个 .ttl 插件描述文件

## 遇到的问题

1. **libsndfile 不可用**: 制品仓未发布 libsndfile，将其设为可选依赖，录音功能优雅降级
2. **X11 不可用**: OHOS 平台无 X11，禁用 GUI 构建 (BUILD_GUI=OFF)
3. **LV2 头文件路径不兼容**: 新版 LV2 使用新路径结构，创建兼容性符号链接
4. **CMake 版本兼容**: cmake_minimum_required(VERSION 2.6) 对 cmake 4.x 太旧，使用 CMAKE_POLICY_VERSION_MINIMUM=3.5
5. **CMake 不识别 HarmonyOS**: 设置 CMAKE_SYSTEM_NAME=Linux 绕过
6. **clang 路径问题**: 使用 Conan 工具链文件指定正确的 OHOS SDK clang 路径
---

**编译结束**: 2026-08-19 10:52
**最终状态**: built
