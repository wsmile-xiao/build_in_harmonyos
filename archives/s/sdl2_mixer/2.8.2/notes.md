# sdl2_mixer 2.8.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build sdl2_mixer 2.8.2 --url=https://github.com/libsdl-org/SDL_mixer/archive/refs/tags/release-2.8.2.tar.gz
```

### 2. 源码补丁
需要对 config.guess 和 config.sub 添加 OHOS triplet 支持:
- config.guess: 添加 `__OHOS__` LIBC检测 和 `*:HarmonyOS:*:*` 系统检测
- config.sub: 添加 `ohos-linux` triplet 支持

### 3. CMake 配置与编译
使用 CMake 而非 autotools（autotools的config.status在HMDFS上有权限问题）:

**静态库构建:**
```bash
mkdir -p cmake-build && cd cmake-build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DSDL2MIXER_CMD=OFF \
  -DSDL2MIXER_MOD=OFF \
  -DSDL2MIXER_GME=OFF \
  -DSDL2MIXER_MIDI_FLUIDSYNTH=OFF \
  -DSDL2MIXER_SAMPLES=OFF \
  -DSDL2MIXER_WAVPACK=OFF \
  -DSDL2MIXER_OPUS=OFF \
  -DSDL2MIXER_DEPS_SHARED=OFF
make -j2
make install DESTDIR=$TEST_PREFIX
make install
```

**共享库构建:**
```bash
mkdir -p cmake-build-shared && cd cmake-build-shared
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_SHARED_LIBS=ON \
  ... (same disabled options)
make -j2
make install DESTDIR=$TEST_PREFIX
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS系统 | OHOS triplet未被GNU config支持 | 添加E007补丁：__OHOS__检测 + HarmonyOS系统识别 → aarch64-unknown-linux-ohos |
| 2 | autotools config.status权限错误 | HMDFS不支持config.status创建临时子目录 | 改用CMake构建系统 |
| 3 | opusfile.h编译失败：找不到ogg/ogg.h | ogg头文件缺失（ogg.pc和ogg/ogg.h不存在） | 禁用Opus支持(SDL2MIXER_OPUS=OFF) |
| 4 | cmake找不到libxmp | libxmp在OHOS上无预编译包 | 禁用MOD支持(SDL2MIXER_MOD=OFF) |
| 5 | cmake找不到wavpack | wavpack在OHOS上无预编译包且vendored目录为空 | 禁用WavPack支持(SDL2MIXER_WAVPACK=OFF) |
| 6 | GitHub下载超时 | 网络限制 | 使用curl手动下载后放到~/tmp/builds/目录 |

## 源码修改

- `build-scripts/config.guess`: 添加__OHOS__ LIBC检测和HarmonyOS系统case分支
- `build-scripts/config.sub`: 添加ohos-linux triplet支持

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| SDL2 | 2.30.10 | 已安装(pkg-config) |
| libogg | N/A | 头文件缺失 |
| libvorbis | N/A | 不需要（使用stb_vorbis内置） |
| libFLAC | N/A | 不需要（使用dr_flac内置） |
| minimp3 | N/A | 内置 |
| timidity | N/A | 内置 |

## 启用的音频格式

| 格式 | 编解码器 | 来源 |
|------|----------|------|
| WAVE | built-in | 内置 |
| OGG Vorbis | stb_vorbis | 内置 |
| FLAC | dr_flac | 内置 |
| MP3 | minimp3 | 内置 |
| MIDI | timidity | 内置 |

## 禁用的音频格式

| 格式 | 原因 |
|------|------|
| MOD | 无libxmp预编译包 |
| Opus | ogg头文件缺失 |
| WavPack | 无预编译包且vendored空 |
| GME | 无预编译包 |
| FluidSynth MIDI | 无预编译包 |

## 验证结果

```bash
# 编译链接验证
$ clang test.c -I$PREFIX/include/SDL2 -L$PREFIX/lib -lSDL2_mixer -lSDL2 -lm -pthread -o test
# 成功链接

# 库文件检查
$ ls $PREFIX/lib/libSDL2_mixer*
libSDL2_mixer.a  libSDL2_mixer.so

# pkg-config验证
$ pkg-config --modversion SDL2_mixer
2.8.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libSDL2_mixer.a | 497KB | 静态库 |
| libSDL2_mixer.so | 379KB | 共享库 |
| SDL_mixer.h | 11KB | 头文件 |
| SDL2_mixer.pc | - | pkg-config文件 |

## 注意事项

1. SDL2_mixer必须与SDL2 2.30.10配合使用
2. ogg头文件缺失导致Opus格式不可用，需要先安装libogg才能启用Opus
3. autotools构建在OHOS上不工作（config.status权限问题），必须使用CMake
4. vendored（external/）子目录为空（git submodule未初始化），所有编解码器必须使用内置或系统库
---

**编译结束**: 2026-05-26 21:38
**最终状态**: built
