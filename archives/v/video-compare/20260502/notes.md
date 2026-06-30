# video-compare 20260502 适配笔记

## 编译环境
- 构建系统: makefile (简单Makefile，无configure)
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

video-compare 使用简单的Makefile构建，无configure/cmake脚本。通过传递make参数编译：

```bash
source .build-context-video-compare-20260502
cd $BUILD_SRC_DIR
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
make CXX=clang++ USE_PKG_CONFIG=1 \
  CXXFLAGS="-g3 -Ofast -std=c++14 -D__STDC_CONSTANT_MACROS -Wall -Wextra -Wno-deprecated -Wno-deprecated-declarations -Wdisabled-optimization -Wctor-dtor-privacy -Woverloaded-virtual -Wno-unused -Wno-missing-field-initializers -I$DEFAULT_PREFIX/include" \
  LDLIBS="-pthread -L$DEFAULT_PREFIX/lib $(pkg-config --libs libavformat libavcodec libavfilter libavutil libswscale libswresample sdl2 SDL2_ttf)"
```

安装：
```bash
cp video-compare $TEST_PREFIX/$DEFAULT_PREFIX/bin/video-compare
llvm-strip $TEST_PREFIX/$DEFAULT_PREFIX/bin/video-compare
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺ffmpeg依赖 | ffmpeg未预装 | 安装ffmpeg 8.1.1预编译包 (`curl install.sh | sh -s -- ffmpeg 8.1.1`) |
| 2 | 缺SDL2依赖 | SDL2未预装 | 安装SDL2 2.30.0预编译包 (`curl install.sh | sh -s -- SDL2 2.30.0`) |
| 3 | 缺SDL2_ttf依赖 | SDL2_ttf无预编译包 | 手动编译SDL2_ttf 2.24.0 |
| 4 | SDL2_ttf链接失败(缺libpng) | freetype静态库依赖libpng | 在SDL2_ttf CMakeLists.txt中添加libpng和zlib链接 |
| 5 | SDL2_ttf configure失败(config.guess) | HarmonyOS平台未识别(E007) | 使用patch-autotools-ohos.pl打补丁 |
| 6 | SDL2_ttf autotools install失败 | HMDFS权限问题 | 改用cmake构建SDL2_ttf |
| 7 | makefile默认g++ | 不支持鸿蒙 | 传递CXX=clang++参数 |

## 源码修改

### SDL2_ttf 2.24.0 (依赖)
- config.guess: 添加HarmonyOS检测(E007补丁)
- config.sub: 添加ohos-linux三元组(E007补丁)
- CMakeLists.txt: 添加libpng和zlib链接(freetype静态库依赖)

### video-compare 20260502 (本软件)
- 无源码修改，通过make参数覆盖编译器/路径

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|---------|
| ffmpeg | 8.1.1 | 预编译包 |
| SDL2 | 2.30.0 | 预编译包 |
| SDL2_ttf | 2.24.0 | 手动编译(cmake) |
| freetype | 2.14.3 | 预装(静态) |
| libpng | 1.6.43 | 预编译包(共享) |

## 验证结果

```bash
$DEFAULT_PREFIX/bin/video-compare --version
# 输出: video-compare 20260502-valencia

pkg-config --modversion SDL2_ttf
# 输出: 2.24.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| video-compare-20260502-ohos-aarch64.tar.gz | ~24MB | 预编译包(已strip) |
| video-compare-20260502-ohos-aarch64-debug.tar.gz | ~518KB | debug符号包 |

## 注意事项

- video-compare使用简单Makefile，构建需通过make参数覆盖编译器和路径
- USE_PKG_CONFIG=1启用pkg-config自动获取依赖库链接参数
- SDL2_ttf作为共享库(.so)编译，被打包进video-compare的预编译包
- HMDFS文件系统不支持直接cp覆盖已有文件，需先rm再cp
---

**编译结束**: 2026-05-25 22:27
**最终状态**: built
