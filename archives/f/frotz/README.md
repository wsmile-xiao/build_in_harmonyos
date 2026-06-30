# Frotz

## 简介

Frotz 是一个 Z-machine 解释器，用于运行 Infocom 和其他 Z-machine 格式的互动小说游戏。Z-machine 是 Infocom 公司为其文字冒险游戏设计的虚拟机架构，Frotz 支持所有版本的 Z-code 游戏（包括 V6）。

## 功能概述

- 支持 curses、Dumb 和 SDL 三种用户界面
- 播放所有 Z-code 游戏版本（V1-V8）
- 音频支持（通过 libao）
- 图形显示（通过 SDL）
- 配置文件支持
- 用户可配置的错误检查
- UTF-8 Unicode 支持

## OHOS 适配要点

### 构建系统

- Frotz 使用 Makefile 构建系统（非 autoconf），需要手动设置 PREFIX 和编译参数
- 无 configure 脚本，直接编辑 Makefile 或通过 make 参数传递配置

### 依赖处理

- 需要 ncursesw 静态库，需手动设置 `CURSES_CFLAGS` 和 `CURSES_LDFLAGS`
- 音频依赖（libao、libmodplug、libsamplerate、libsndfile、libvorbis）可选，建议禁用以简化编译：`SOUND_TYPE=none`

### 平台适配

- 需要添加 `#include <stdbool.h>` 解决 true/false 未定义问题
- KEY_MOUSE 在静态 ncursesw 编译时可能缺失，需手动定义 `KEY_MOUSE = 0631`
- 需要设置 `_DEFAULT_SOURCE` 和 `_XOPEN_SOURCE=600` 启用 strdup 等函数
- OpenHarmony 缺少 install 命令，需使用手动 cp + chmod

### 编译参数示例

```bash
make PREFIX=~/usr/local \
     SOUND_TYPE=none \
     CC=clang \
     CFLAGS="-Wall -std=c99 -O3 -g -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=600" \
     CURSES_CFLAGS="-I~/usr/local/include -D_XOPEN_SOURCE_EXTENDED" \
     CURSES_LDFLAGS="-L~/usr/local/lib -lncursesw"
```

## 依赖关系

### 编译依赖

- ncursesw（静态库）

### 运行依赖

- ncursesw（运行时库）

## 参考资料

- 官网：https://661.org/proj/if/frotz/
- GitLab：https://gitlab.com/DavidGriffith/frotz
- IF Archive：http://www.ifarchive.org/if-archive/infocom/interpreters/frotz/