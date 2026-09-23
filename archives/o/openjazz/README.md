# openjazz

## 简介
OpenJazz —— Jazz Jackrabbit 1（《爵士兔》）游戏引擎的开源重制版（GPL-2.0）。
C++14 + CMake 构建，产物为可执行文件 `OpenJazz`。

## OHOS 适配
- CMake 构建（cmake_minimum_required 3.18...4.2），C++14，产物 `OpenJazz` 可执行文件
- E092：CMake 不识别 HarmonyOS 平台，配方 generate() 用 `CMAKE_SYSTEM_NAME=Linux` 兼容（走 UNIX 分支 install）
- SDL2 走 conan CMakeDeps（sdl2 包 cmake_file_name=SDL2，`find_package(SDL2)` 直接命中）
- 音频后端为**内嵌 psmplug + SDL_audio**（源码实证，不依赖 SDL_mixer）；
  内嵌库 argparse/miniz/psmplug/stb 全部 STATIC 自包含，无额外外部依赖
- 网络默认自动检测原生 sockets（sys/socket.h），无则自动禁用
- 可执行文件 ELF 需签名后才可运行（test_package 内处理，binary-sign-tool）

## 依赖
- sdl2/2.30.10（ohpcd 制品仓）

## 功能验证
- test_package 消费者测试 4 项断言：二进制存在且可执行、`-v`、`--version` 版本输出
  含 "OpenJazz 20260301"、`--help` 输出 usage 与 Engine options
  （均为 argparse 纯 IO 退出路径，OHOS ELF 签名后真实执行）
- W3 本地 CI：conan create + test_package + L0-L5 门禁全 PASS

## 参考
- 上游: https://github.com/AlisterT/openjazz
