# sensorfw

sensorfw 是 Sailfish OS（原 MeeGo / Nokia N9）的传感器框架：一个常驻守护进程
`sensorfwd`（源码内称 sensord）负责采集设备传感器数据，客户端通过 D-Bus 与之
交互，采集链路则由运行期 `dlopen()` 的插件组成。

## 功能概述

- **sensord 守护进程**（`sensorfwd`）：传感器会话管理、采样率控制、数据通路调度、
  电源管理协作、D-Bus 服务暴露与自定义 UNIX socket 快通道。
- **数据通路框架**：`DeviceAdaptor` → `Sensor`/`Chain`（可串联过滤器）→
  `RingBuffer` → 客户端会话，按引用计数共享 adaptor / chain 实例。
- **插件体系**（四类，均按类别编译成独立 `.so`，运行期加载）：
  - `adaptors/` —— 设备适配层（accelerometer、als、gyroscope、magnetometer、
    proximity、pressure、humidity、lid、tap、touch、temperature、iio 等 21 个）
  - `sensors/` —— 传感器定义（15 个）
  - `chains/` —— 组合链路（accelerometer、compass、orientation、magcalibration、
    sample 等）
  - `filters/` —— 数据处理过滤器（去偏、坐标对齐、旋转、降采样、方向解释等 7 个）
- **客户端 API**：`libsensorclient-qt5` 提供 Qt 风格接口
  （`SensorManagerInterface` + 各 `*SensorInterface`），并提供 `sensord-qt5.pc`。
- **数据类型库**：`libsensordatatypes-qt5`（`TimedXyzData`、`PoseData`、
  `CompassData` 等可序列化数据类型）供客户端与服务端共用。

## OHOS 适配

构建系统为 **qmake**（顶层 `sensorfw.pro` 是 `TEMPLATE = subdirs` 递归工程）。
在 OHOS PC（aarch64）上需要四个 portability 补丁，详见
`0.15.2/conandata.yml` 与 `0.15.2/notes.md`：

1. **libudev 查找改为环境变量优先**（`adaptors/iioadaptor/iioadaptor.pro`）。
   交叉编译下 qmake 的 `pkgConfigExecutable()` 返回空，且 `libudev-zero` 的
   `.pc` 里 `prefix=` 是打包机的陈旧路径；改为由构建系统经环境变量提供头文件
   与库目录，未提供时保持原 pkg-config 回退。
2. **systemd 集成可选**（`sensord/sensord.pro` + `sensord/main.cpp`）。
   OHOS 无 systemd，`PKGCONFIG += libsystemd` 会直接失败；把链接与 `sd_notify()`
   就绪通知放到 `CONFIG+=systemd` / `HAVE_SYSTEMD` 之后。
3. **插件自带对框架库的 DT_NEEDED**（四类 `*-config.pri` + `sensorfw.pro`
   的 SUBDIRS 顺序）。
   **这是本平台最关键的适配点**：HarmonyOS/musl 的动态加载器解析 `dlopen()`
   对象的未定义符号时，**只查该对象自身的 DT_NEEDED 闭包**，主程序的符号、
   主程序 DT_NEEDED 的库、`RTLD_GLOBAL`/预加载的库都不可见
   （见 `0.15.2/notes.md` 的最小复现）。sensorfw 的插件引用
   `libsensorfw-qt5` 导出的 `InputDevAdaptor` / `AbstractChain` /
   `AbstractSensor` / `PluginBase`，但上游**不链接**框架库、依赖宿主进程提供
   符号 —— 在 glibc 上成立，在 musl 上插件 100 % 加载失败
   （`Error relocating ...: symbol not found`），即守护进程无法加载任何插件。
   修复方式与 `archives/l/libnfsidmap-ldap/2.6.4` 同因同解：让插件链接框架库。

### 已知问题 / 与 Linux 的差异

- **插件目录是编译期烘焙的绝对路径**：`core/core.pro` 把
  `PLUGIN_DIRECTORY` 定义为 `$$[QT_INSTALL_LIBS]/sensord-qt5`，即构建时那个
  Qt 包的 `lib/` 目录。Conan 包被搬运后该路径必然悬空。本包把插件装到
  `<pkg>/lib/sensord-qt5/`，消费者需把该目录布置到烘焙位置，或设置
  `SENSORFW_LIBRARY_PATH`（注意上游语义是**前缀**，会与烘焙的绝对路径拼接）。
- **以包目录作为 `LD_LIBRARY_PATH` 直接运行动态产物会失败**：本平台加载器
  对 `.so` 版本化符号链接返回 `Permission denied`（实测），Qt 依赖包内的
  `libQt5Core.so.5` 等恰是符号链接。运行前需按 DT_NEEDED 闭包把库解引用
  （`cp -L`）复制到临时目录。
- 上游测试套件（`tests/`，QtTest）中涉及硬件/服务的一组用例需要在装有
  sensord、D-Bus 与传感器配置（`/etc/sensorfw/sensord.conf`）的目标设备上
  运行，构建机不可复现，具体逐项原因见 `0.15.2/notes.md`。

## 依赖关系

编译依赖（Conan）：

| 依赖 | 版本 | 用途 |
|------|------|------|
| `qt` | 5.15.19.1 | Qt5Core / Qt5Network / **Qt5DBus** / Qt5Test；提供 `mkspecs/harmonyos-clang` |
| `libudev-zero` | 1.0.4 | `iioadaptor` 枚举 input 设备（静态库） |

运行依赖：Qt5（Core / Network / DBus）、内核 input/uinput 子系统、D-Bus 系统总线。
`libudev-zero` 为静态链接，无运行期依赖。

## 参考资料

- 上游仓库：<https://github.com/sailfishos/sensorfw>
- 本次适配版本：标签 `0.15.2`
- 本仓相关先例：
  - `archives/l/libnfsidmap-ldap/2.6.4` —— 插件缺宿主库 `DT_NEEDED` 的同因同解
  - `archives/y/yasw/0.6` —— `qt/5.15.19.1` 的 qmake 消费范式与加载器符号链接实测
