# rsgain 3.6-r2 适配笔记

## 编译环境
- 构建系统: custom（直接编译源文件，绕过 upstream CMake）
- 编译日期: 2026-07-22
- 编译器: clang/clang++（OHOS 6.0 SDK，clang 15）
- 目标平台: OHOS 6.0 (aarch64, libc++, Release)
- 状态: built（待鸿蒙环境验证）

## 适配方案概述

rsgain 是一个 ReplayGain 2.0 响度归一化工具，依赖 5 个第三方库：
- **FFmpeg** (8.1.2) — 音频解码（libavformat/libavcodec/libswresample/libavutil）
- **taglib** (2.3) — 音频标签读写
- **libebur128** (1.2.6) — EBU R128 响度测量
- **inih** (r58) — INI 配置文件解析
- **fmt** (10.2.1) — C++ 格式化库（替代 std::format）

由于这 5 个依赖在 OHOS Conan 制品仓中均不存在，采用**内嵌构建所有依赖**方案：
所有依赖源码与 rsgain 源码一起下载，在 build() 方法中依次构建为静态库，
最后与 rsgain 的 5 个 C++ 源文件静态链接为单一二进制。

参考了 unpaper/7.0.0 的内嵌 FFmpeg 构建模式。

## 编译步骤

### 1. 下载源码
- rsgain 3.6 源码（tar.xz）
- FFmpeg 8.1.2 源码（tar.xz）
- taglib 2.3 源码（tar.gz）
- libebur128 1.2.6 源码（tar.gz）
- inih r58 源码（tar.gz）
- fmt 10.2.1 源码（zip）

### 2. 构建 FFmpeg（autotools，最小化音频配置）
```bash
# 应用 harmonyos target_os 补丁
patch -p1 < patches/0001-ffmpeg-configure-harmonyos.patch

# 配置：禁用所有，仅启用 rsgain 支持的音频格式解码器/demuxer/解析器
./configure --cc=clang --prefix=$FF_PREFIX \
  --disable-everything \
  --enable-decoder=mp3float,flac,vorbis,opus,aac,wmav1,wmav2,pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,alac,wavpack,ape,tak,mpc7,mpc8 \
  --enable-demuxer=mp3,flac,ogg,mov,mp4,aiff,wav,wv,ape,mpc,asf \
  --enable-parser=mpegaudio,flac,vorbis,opus,aac,aac_latm \
  --enable-protocol=file \
  --enable-filter=aresample \
  --enable-swresample --disable-zlib --disable-iconv \
  --disable-doc --disable-programs --disable-shared --enable-static \
  --disable-avdevice --disable-avfilter --disable-swscale --disable-vulkan

make -j2 && make install
```

### 3. 构建 fmt（CMake，静态库）
```bash
cmake $FMT_SRC -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_INSTALL_PREFIX=$FMT_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DFMT_DOC=OFF -DFMT_TEST=OFF -DFMT_CUDA=OFF -DBUILD_SHARED_LIBS=OFF
make -j2 && make install
```

### 4. 构建 inih（直接编译）
```bash
# inih r58: ini.c (C) + cpp/INIReader.cpp (C++ wrapper)
clang -c -O2 -I$INIH_SRC ini.c -o ini.o
clang++ -std=c++20 -c -O2 -I$INIH_SRC -I$INIH_SRC/cpp INIReader.cpp -o INIReader.o
llvm-ar rcs libinih.a ini.o INIReader.o
```

### 5. 构建 libebur128（CMake，静态库）
```bash
cmake $EBUR_SRC -DCMAKE_C_COMPILER=clang \
  -DCMAKE_INSTALL_PREFIX=$EBUR_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DBUILD_SHARED_LIBS=OFF -DENABLE_TESTS=OFF
make -j2 && make install
```

### 6. 构建 taglib（CMake，静态库）
```bash
cmake $TAG_SRC -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_INSTALL_PREFIX=$TAG_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF -DWITH_ZLIB=OFF
make -j2 && make install
```

### 7. 生成 config.h
手动生成 config.h（替换 CMake 的 configure_file），包含：
- PROJECT_NAME = "rsgain"
- EXECUTABLE_TITLE = "rsgain"
- PROJECT_VERSION = "3.6"
- PROJECT_URL = "https://github.com/complexlogic/rsgain"
- preset 目录在运行时根据 `/proc/self/exe` 相对定位到 `../share/rsgain/presets`

### 8. 编译 rsgain 源文件（C++20）
```bash
# 5 个 .cpp 文件：rsgain.cpp, scan.cpp, output.cpp, tag.cpp, easymode.cpp
clang++ -std=c++20 -O2 -D_GNU_SOURCE \
  $(pkg-config --static --cflags libavformat libavcodec libswresample libavutil) \
  -I$RSGAIN_SRC -I$BUILD_DIR -I$FMT_PREFIX/include -I$INIH_PREFIX/include \
  -I$EBUR_PREFIX/include -I$TAG_PREFIX/include \
  -c rsgain.cpp -o rsgain.o
# ... 对每个 .cpp 文件重复
```

### 9. 静态链接 rsgain 二进制
```bash
clang++ -static -o rsgain *.o \
  -L$FF_PREFIX/lib -L$FMT_PREFIX/lib -L$INIH_PREFIX/lib \
  -L$EBUR_PREFIX/lib -L$TAG_PREFIX/lib \
  -ltag -lebur128 -linih -lfmt \
  -lpthread -lm -ldl \
  $(pkg-config --static --libs libavformat libavcodec libswresample libavutil)
```

### 10. ELF 签名
```bash
llvm-objcopy --remove-section .codesign rsgain
binary-sign-tool sign -inFile rsgain -outFile rsgain.signed -selfSign 1
mv rsgain.signed rsgain
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 5 个依赖在 OHOS Conan 制品仓中均不存在 | OHOS 生态尚在建设中 | 采用内嵌构建方案，所有依赖从源码编译为静态库 |
| 2 | OHOS clang 15 不支持 C++23 std::format | rsgain 可选使用 std::format（需 C++23） | 不定义 USE_STD_FORMAT，使用 fmt 库替代 |
| 3 | FFmpeg configure 不识别 harmonyos 目标平台 | FFmpeg 原生不支持 OHOS | 应用 portability 补丁添加 harmonyos target_os case |
| 4 | upstream CMake 需要 pkg-config 文件 | 内嵌构建不生成 .pc 文件（除 FFmpeg 外） | 绕过 CMake，直接编译 5 个 .cpp 文件 |
| 5 | config.h 需要 CMake 的 configure_file 生成 | 绕过了 CMake | 手动生成 config.h，替换模板变量 |
| 6 | FFmpeg 补丁版本匹配 | 补丁基于 FFmpeg 8.1.2 创建，rsgain 同样使用 8.1.2 | 直接复用 unpaper/7.0.0 已验证的补丁，无需调整行号 |
| 7 | PRESETS_DIR 指向 Conan build 阶段临时 package_folder | 二进制安装到缓存后临时绝对路径失效 | 通过 `/proc/self/exe` 相对定位 `../share/rsgain/presets` |
| 8 | CI #10290 conan create 在 build() 第 212 行失败（libebur128 cmake 配置阶段） | libebur128 1.2.6 的 CMakeLists.txt 使用 `cmake_minimum_required(VERSION 2.8.12)`，CMake 4.0 移除了对 < 3.5 的兼容，直接报 `Compatibility with CMake < 3.5 removed` 终止；`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 只能解决 policy 兼容，无法绕过 minimum_required 版本检查 | 新增 0003 补丁，将根 CMakeLists.txt 与 test/CMakeLists.txt 的 `cmake_minimum_required` 从 2.8.12 提升到 3.5（与 wangle recipe 同样手法） |
| 9 | test.sh `set -euo pipefail` 与 `|| rc=$?` 语义冲突（评审 P2） | `set -e` 会在命令返回非零时提前退出，与设计意图（允许非零退出码、仅拦截 ≥128 信号崩溃）矛盾 | 去掉 `set -e`，保留 `set -uo pipefail`，`rsgain --version` 用 `if !` 显式判断，`rsgain easy` 用 `|| rc=$?` 接住退出码后再判定 |

## 源码修改

### patches/0001-ffmpeg-configure-harmonyos.patch
为 FFmpeg configure 增加 harmonyos 目标平台支持：
- 在 `case $target_os in` 中添加 `harmonyos` case（enable section_data_rel_ro, enable_weak linux_perf, add_cppflags -D_GNU_SOURCE）
- 在 ARM 指令集检查中添加 harmonyos 到允许列表
- 在 ffnvcodec/cuvid 检查中添加 harmonyos 到允许列表

注意：此补丁直接复用 unpaper/7.0.0 的 FFmpeg 8.1.2 补丁，版本完全匹配，无需调整行号。

### patches/0002-locate-presets-relative-to-executable.patch
在 Unix/OHOS 平台通过 `/proc/self/exe` 获取 rsgain 二进制路径，并从 `bin/../share/rsgain/presets` 加载命名 preset，避免依赖构建阶段临时路径。

### patches/0003-libebur128-cmake-minimum-required-3.5.patch
修复 CI #10290 构建失败（build() 第 212 行 libebur128 cmake 配置阶段）：
- libebur128 1.2.6 根 `CMakeLists.txt`：`cmake_minimum_required(VERSION 2.8.12 FATAL_ERROR)` → `3.5 FATAL_ERROR`
- libebur128 1.2.6 `test/CMakeLists.txt`：`cmake_minimum_required(VERSION 2.8.12)` → `3.5`

根因：CMake 4.0 移除了对 `cmake_minimum_required < 3.5` 的兼容，直接报 `Compatibility with CMake < 3.5 removed` 终止配置。`-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 只能解决 policy 兼容性，无法绕过 minimum_required 版本检查。此补丁与 wangle recipe 的 `0001-CMakeLists.txt.patch` 采用相同手法（提升 minimum_required 到 3.5）。补丁未引入 `#ifdef __OHOS__`，属 portability 类型。

## 依赖版本

| 依赖 | 版本 | 构建系统 | 构建方式 |
|------|------|----------|----------|
| FFmpeg | 8.1.2 | autotools | 静态库，最小化音频配置 |
| taglib | 2.3 | CMake | 静态库 |
| libebur128 | 1.2.6 | CMake | 静态库 |
| inih | r58 | 直接编译 | 静态库（ini.c + INIReader.cpp） |
| fmt | 10.2.1 | CMake | 静态库 |

## 验证结果

待鸿蒙环境验证。预期验证命令：
```bash
rsgain --version
# 应输出 rsgain 3.6 及所有依赖库版本信息

rsgain easy --quiet /path/to/audio
# 应能扫描音频文件并计算 ReplayGain

rsgain easy --preset default /path/to/audio
# 应输出 Applying preset 'default'，并从包内 share/rsgain/presets 加载配置
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/r/rsgain/commands.json | 命令行工具声明（软件级，R38） |
| archives/r/rsgain/3.6-r2/conanfile.py | Conan 配方（内嵌构建所有依赖） |
| archives/r/rsgain/3.6-r2/conandata.yml | 源码 + 补丁声明 |
| archives/r/rsgain/3.6-r2/patches/0001-ffmpeg-configure-harmonyos.patch | FFmpeg harmonyos 补丁 |
| archives/r/rsgain/3.6-r2/patches/0002-locate-presets-relative-to-executable.patch | preset 运行时相对路径补丁 |
| archives/r/rsgain/3.6-r2/test_package/ | L1 消费者测试 |
| archives/r/rsgain/3.6-r2/manifest.yaml | 编译元数据 |
| archives/r/rsgain/3.6-r2/notes.md | 适配笔记（本文件） |

## 注意事项

1. **SHA256 已填充**：所有依赖的 SHA256 已通过 curl 下载源码包并用 Python hashlib 计算填充。
2. **FFmpeg 版本**：使用 8.1.2（与 unpaper/ffprobe 一致），可直接复用已验证的 harmonyos 补丁。
3. **zlib 依赖**：OHOS 仅提供共享 libz.so 无 libz.a，无法用于 -static 链接。FFmpeg（--disable-zlib）和 taglib（-DWITH_ZLIB=OFF）均禁用 zlib，MP4/M4A 压缩 ID3v2 帧处理受限，但核心 ReplayGain 扫描与标签写入功能不受影响。
4. **ELF 签名**：本地环境无法签名，CI/release worker 会自动签名。签名失败时清理临时文件。
5. **preset 文件**：package() 方法会复制 config/presets/*.ini 到 share/rsgain/presets/，运行时根据可执行文件路径定位该目录。
6. **test.sh 崩溃检测**：`rsgain easy` 的退出码 >= 128 表示进程被信号杀死（崩溃），测试会报告 FAIL。普通非零退出码（如 WAV 不支持标签写入）不视为失败。
7. **libebur128 / inih 源码 SHA256 稳定性风险（已知，已评估）**：这两个依赖的上游 GitHub Release（`jiixyj/libebur128` v1.2.6、`benhoyt/inih` r58）均未上传任何独立的 release asset（已通过 GitHub Releases API 确认 `assets: []`），上游亦无 SourceForge/官网等其它稳定 tarball 来源，因此只能使用 GitHub 自动生成的 archive tarball（`/archive/refs/tags/...`）。该路径的 tarball 由 GitHub 按需生成，其压缩参数 / 文件时间戳 / 内部排序可能随 GitHub 基础设施升级而漂移，导致同一 URL 在不同时间下载得到不同 SHA256。本配方 `conandata.yml` 中记录的 SHA256 为构建时实际下载文件的真实校验值（已校验通过）。**风险缓解**：若后续 `conan create` 在 source 阶段因 SHA256 校验失败而中断，重新下载对应 tarball 并用 `python3 -c "import hashlib;print(hashlib.sha256(open('xxx.tar.gz','rb').read()).hexdigest())"` 计算新值，更新 `conandata.yml` 中对应条目即可恢复构建。其余 4 个依赖（rsgain / FFmpeg / taglib / fmt）均使用稳定的 release asset 或官方站点 URL，不受此风险影响。
