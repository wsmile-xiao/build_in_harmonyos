# fceux

> 任天堂 NES/Famicom 全功能模拟器，2.6.6 维护版本（Qt/SDL 跨平台版）。

## 简介

FCEUX 是开源 NES/Famicom/Dendy 模拟器，以高仿真精度与面向高级用户的调试工具链
（调试器、追踪日志、TAS 编辑器、Lua 脚本、电影录制、状态记录器）著称。
2.6.6（2023-08-26）主要为映射器与模拟核心的维护更新，并包含 Qt/SDL 专属新功能
（状态记录器、libarchive 7zip 读档、ld65 调试符号加载、QPainter 视频驱动等）。

## OHOS 适配要点

- CMake 构建的 Qt5 图形应用包，仅发布 `fceux` 二进制（application 包，R38）。
- 硬依赖全部来自制品仓已发布配方：`qt5-qtbase/5.15.2.2`（Qt Widgets + OpenGL 前端；
  基线 `5.15.2` 在制品仓无 OHOS 二进制，真机预检报 "No compatible configuration
  found"，全仓 Qt 消费方统一用 `5.15.2.2`）、
  `sdl2/2.30.10`（音频/视频/手柄后端）、minizip 1.3.1 内置静态编译（与 ohpcd
  minizip 包同源的 zlib-1.3.1 contrib/minizip；外部 RREV pin 在远端不存在）、
  `zlib/1.3.1.1`
  （系统 zlib，上游 `find_package(ZLIB REQUIRED)`；仓内独有版本，同上游 1.3.1
  源码 + `-fPIC` 静态重建，conancenter 无同版本故自动落 ohpcd，
  `override=True` 统一 qt5-qtbase 传递的 `1.3.1`，gtk4/wv 同式）。
- Lua 使用上游内嵌版本静态编译（`src/lua/`，`LUA_USE_LINUX`），不引入外部 lua 依赖。
- `libarchive`/`x264`/`x265`/`libav` 均为上游可选依赖（`pkg_check_modules` 非 REQUIRED），
  未找到时自动关闭对应功能，不阻塞构建。
- 无头冒烟测试：`QT_QPA_PLATFORM=offscreen fceux --version/--help`
  （上游 `src/drivers/Qt/fceuWrapper.cpp` 在打印后直接 `exit(0)`，不进入 Qt 事件循环，
  与 flameshot/augustus-game 的无头 `--version` 模式同理）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Widgets + OpenGL 前端（5.15.2 无 OHOS 二进制） |
| sdl2 | 2.30.10 | SDL2 音频/视频/输入后端 |
| minizip | 1.3.1 内置（vendored） | 压缩包 ROM 读取（上游 REQUIRED；外部包默认命中 CCI CMake 配方无法在 HarmonyOS 配置且 RREV 在远端不存在，改从 zlib-1.3.1 contrib/minizip 静态内置并自产 minizip.pc） |
| zlib | 1.3.1.1（override） | 系统 zlib（上游 REQUIRED；独有版本自动落 ohpcd，统一 qt5 传递的 1.3.1） |
| bzip2 | 1.0.8#3b49a968（override） | 传递依赖：默认解析到 CCI CMake 配方无法在 HarmonyOS 配置，强制 cataract 已验证的制品仓 revision |
| expat | 2.8.2.1#332af6a48367eceadb1f9cf0c32f340d（override） | 传递依赖（经 dbus）：CCI 修订版拖入 CCI cmake/4.4.3（conandata 无 OHOS 条目），强制 cataract 已验证的制品仓 revision |

## 功能验证

```bash
QT_QPA_PLATFORM=offscreen fceux --version   # 期望输出: 2.6.6
QT_QPA_PLATFORM=offscreen fceux --help      # 退出码 0
```

## 参考

- [上游仓库](https://github.com/TASEmulators/fceux)
- [官网下载页](https://fceux.com/web/download.html)
- [2.6.6 更新日志](https://fceux.com/web/help/WhatsNew266.html)
- [Linux 构建脚本](https://github.com/TASEmulators/fceux/blob/master/pipelines/linux_build.sh)
