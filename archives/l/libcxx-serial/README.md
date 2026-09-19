# libcxx-serial

## 简介

libcxx-serial 是一个跨平台的 C++ 串口（RS-232）访问库，提供简洁的面向对象
API（`serial::Serial`）来读写串行端口，并支持枚举系统串口
（`serial::list_ports()`）。上游为 wjwwood/serial（Debian 源码包名
libcxx-serial），MIT 许可证。

## OHOS 适配

### 适配要点

1. **构建系统替换**：上游 CMakeLists.txt 硬依赖 ROS catkin
   （`find_package(catkin REQUIRED)`），补丁整文件替换为纯 CMake 工程，
   编译 unix 实现（serial.cc + impl/unix.cc + list_ports_linux.cc），
   标准 lib/include 安装；不编 serial_example（纯库包，无 commands.json）。
2. **链接策略**：上游 Linux 分支链接 `rt pthread`（glibc 拆分库）；
   目标平台 libc 已内置 pthread/clock_gettime，无需额外链接。
3. **无平台宏**：补丁未引入 `__OHOS__` 等平台宏，自定义波特率等代码沿用
   上游原有能力守卫（`#ifdef Bxxxx` / `defined(TIOCSSERIAL)`）。

### 与 Linux 差异

- `#include <sys/signal.h>` 产生 sysroot 重定向 warning（重定向到
  signal.h），musl 行为，不影响功能。

### 测试

- 上游 gtest 套件 unix_serial_tests（openpty 回环，4 用例）与
  unix_timer_tests（2 用例）已在设备真机实跑全部通过；
  timer 套件的 short_intervals 为 ±1ms 计时敏感用例，共享设备忙时可能
  出现 ±2ms 调度抖动失败（非功能缺陷）。
- 消费者测试 test_package 链接打包产物并真实调用 list_ports() 与 API 枚举。

## 依赖

无外部依赖（纯 POSIX/C++ 标准库）。
