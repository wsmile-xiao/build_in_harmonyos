# libkcompactdisc

KDE Gear 库，提供与 CD-ROM 光驱交互的接口（音频 CD 播放、碟片状态、
音轨控制），产出 `libKCompactDisc6.so`（CMake 目标 `KCompactDisc6`，
导出配置 `KCompactDisc6Config.cmake`）。

- 上游：https://invent.kde.org/multimedia/libkcompactdisc
- 许可证：LGPL-2.0-or-later（库）+ GPL-2.0-or-later（内嵌 wmlib）
- 源码：https://download.kde.org/stable/release-service/25.12.1/src/libkcompactdisc-25.12.1.tar.xz

## 鸿蒙PC 适配要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台检测；
- E092：注入 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`（SOVERSION 5 库必须有 DT_SONAME）；
- 依赖包均 `cmake_find_mode=none`，手工生成 `conan_cmakedeps_paths.cmake`；
- wmlib 走 `plat_linux.c`（OHOS sysroot 含 `linux/cdrom.h`）；音频后端由宏守卫，
  ALSA（alsa-lib/1.2.16.1）启用，aRts/Sun 后端宏关闭；
- 目标平台无 CD-ROM 硬件：设备枚举返回空列表，属预期行为。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 25.12.1 | published | 2026-09-24 |
