# libhdhomerun

SiliconDust HDHomeRun C library — provides a C API for discovering, configuring,
and streaming from HDHomeRun network-attached TV tuner devices.

- **项目主页**: https://www.silicondust.com/
- **源码仓库**: https://github.com/Silicondust/libhdhomerun
- **许可证**: LGPL-2.1-or-later
- **构建系统**: 自定义 Makefile（非 autotools）
- **产物**: libhdhomerun.so（共享库）、hdhomerun_config（CLI 工具）
- **平台依赖**: 无外部依赖（仅 libc/pthread）

## 已编译版本

| 版本 | 状态 | 日期 | 补丁数 |
|------|------|------|--------|
| 20260313 | published | 2026-06-18 | 3 |

## 补丁说明

1. **0001-Makefile.patch** — CC/STRIP 改为 `?=`，添加 prefix 变量和 install target
2. **0002-configure.patch** — 添加 dummy configure 脚本（兼容构建管线）
3. **0003-hdhomerun_sock_getifaddrs.c.patch** — BSD 专用头文件 `#ifdef` 守卫
