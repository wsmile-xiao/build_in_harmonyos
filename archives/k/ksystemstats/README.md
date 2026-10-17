# ksystemstats

KDE Plasma 的系统统计守护进程。它以 `org.kde.ksystemstats` D-Bus 服务的形式运行，
采集并发布系统传感器数据，供 plasma-systemmonitor 等前端消费。

- **上游**：https://invent.kde.org/plasma/ksystemstats
- **构建系统**：CMake（ECM / KF6 / Qt6 / KSysGuard）
- **许可证**：GPL-2.0-only OR GPL-3.0-only（部分文件 BSD-2-Clause）

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ksystemstats` | 守护进程本体（`org.kde.ksystemstats` D-Bus 服务） |
| `bin/kstatsviewer` | 传感器查看 CLI（`--list` 列出现有传感器） |
| `lib/plugins/ksystemstats/` | 传感器插件（cpu、disk、gpu、memory、network、osinfo、power、pressure） |
| `lib/libdbus-1.so*` | vendor 的共享 libdbus-1（见下） |
| `lib/systemd/user/`、`share/dbus-1/services/` | D-Bus 服务与 systemd 用户单元文件 |

## OHOS 适配

- **平台判定错配**：OHOS clang 目标 `aarch64-linux-ohos` 同时定义 `__OHOS__` 与
  `__linux__`，源码中 `#ifdef Q_OS_LINUX` 分支全部生效；而 conan 把 `os=OHOS`
  映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，上游的 Linux CMake 门控全部为假。
  补丁引入 `KSYSTEMSTATS_LINUX_PLATFORM` 统一两侧判定，从而启用 real Linux 后端
  （`/proc`、`/sys`、rtnetlink、PSI、hwmon），而非退化为空壳插件。
- **共享 libdbus**：`libQt6DBus` 运行期 `dlopen("libdbus-1")`，而本制品仓只发布
  静态 `libdbus-1.a`；配方从官方 dbus 1.14.10 源码编译共享 `libdbus-1.so` 并随包安装，
  否则 `QDBusConnection::sessionBus()` 无法连接、守护进程不可用。
- **会话总线**：OHOS 沙箱禁止 AF_UNIX bind，测试与消费端使用 TCP + ANONYMOUS 的私有会话总线。
- **lm-sensors**：已发布 `libksysguard/6.7.2` 未启用 lm-sensors，不导出
  `KSysGuard::makeSensorsFeatureSensor`，因此 CPU/AMD GPU 温度传感器与 lmsensors
  插件关闭（CPU 使用率/频率、内存、磁盘、网络、压力、电源、osinfo、GPU 枚举均正常）。
  详见版本目录下的 `notes.md`。
- **KIO**：KF6 6.18 系列无可用 kio（`kio/6.26.0` 硬依赖 `kcoreaddons/6.26.0`，与
  `libksysguard/6.7.2` 的依赖集冲突），disks 插件的空闲空间查询改用等价的
  `QStorageInfo` 路径。

## 依赖

- `qtbase/6.11.1.1`（`override=True`，FEATURE_dbus=ON）、`qtdeclarative/6.11.1`、`kservice/6.18.0`
- `kcoreaddons/6.18.0`、`kcrash/6.18.0`、`solid/6.26.0`
- `libksysguard/6.7.2`（KSysGuard::SystemStats/Formatter/ProcessCore、传感器框架）
- `libnl/3.11.0`（rtnetlink）、`eudev/3.2.14`（GPU 设备枚举）、`libdrm/2.4.133`（Intel helper 头文件）
- 构建工具：`ecm/6.26.0`、`dbus/1.14.10.1`（提供 `dbus-daemon` / `dbus-run-session`）

## 验证

- 上游 CTest：3/3 通过（100%）——`ksystemstatstest`（6 个 QTest 函数，含 D-Bus API）、
  `TestLinuxCpu`、`nvidiatest`。
- 消费端 test_package：启动打包的守护进程与私有会话总线，用打包的 `kstatsviewer`
  断言 274 个真实传感器（覆盖 cpu/memory/disk/network/os/power/pressure/gpu 容器）
  且 `cpu/all/usage` 返回实时值。
