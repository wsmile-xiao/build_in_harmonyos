# ksystemstats 6.7.2 适配笔记

## 编译环境

- 构建系统: cmake (ECM / KF6 6.18 系列 / Qt6 / KSysGuard)
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, -std=c++20 -stdlib=libc++)
- 生成器: Ninja（GNU make 4.4.1 的 jobserver 走 mkfifo，OHOS 沙箱拒绝 EPERM）
- 状态: built
- conan: `conan create archives/k/ksystemstats/6.7.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（EXIT=0）

## 编译步骤

1. `conan source` 下载上游 tarball（sha256 校验）+ 官方 dbus 1.14.10 源码（用于 vendor 共享 libdbus）。
2. `conan create` 内部：
   - `apply_conandata_patches` 顺序应用 0001-0017；
   - 编译 vendor 共享 `libdbus-1.so`（`--target dbus-1`，TCP 会话总线运行期依赖）；
   - CMake configure（Qt6 / KF6 6.18 / KSysGuard / NL / UDev / libdrm 全部命中）→
     `cmake.build()`（104 个目标）→ `_run_upstream_tests()`（3 个上游 CTest）→
     `package()` 安装（并附带 vendor 的 libdbus）→ test_package 消费端验证。

## 核心问题：平台判定错配（本包最关键的一条）

OHOS clang 目标三元组为 `aarch64-linux-ohos`，**同时定义 `__OHOS__` 与 `__linux__`**，
因此 Qt 的 `qsystemdetection.h` 让 `Q_OS_LINUX` 成立，源码里所有 `#ifdef Q_OS_LINUX`
分支都会被编译；而 conan 把 `settings.os=OHOS` 映射成 `CMAKE_SYSTEM_NAME=HarmonyOS`，
上游所有 `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 门控统统为假。

结果：源码走 Linux 分支（引用 `LinuxCpuPluginPrivate`、`RtNetlinkBackend`、
`<sensors/sensors.h>`），而这些源文件却被 CMake 排除 → 编译/链接必然失败。

处理：补丁 0001 引入单一 `KSYSTEMSTATS_LINUX_PLATFORM`（Linux 或 HarmonyOS），
其余补丁把它用于 pressure / cpu / memory / network / gpu / cpu-autotests 各门控。
这既修复了错配，也让桥接的 Linux 后端（/proc、sysfs、rtnetlink、PSI、hwmon）
真正启用，而不是退化成本文之外的空壳（R40）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(KF6 ... KIO ...)` 失败 | 上游顶层硬性要求 KIO，而 KF6 6.18 系列没有可用 kio | 0001：把 KIO 纳入 `KSYSTEMSTATS_USE_KIO` 开关；配方置 OFF |
| 2 | KF6 版本墙 | 上游要求 KF6 ≥ 6.26.0，已发布矩阵是 6.18 | 0001：`KF6_MIN_VERSION` 降为 6.18.0（libksysguard 前例） |
| 3 | `find_package(KSysGuard)` 报 `Qt6::Qml`/`KF6::Service` 目标不存在 | KSysGuardConfig.cmake 只 `find_dependency` 了 Qt6Core/Network/Widgets 与 KF6Config/KF6I18n，但其导出目标的链接接口含 Qt6::Qml/Qt6::Quick/KF6::Service | 0001：在 `find_package(KSysGuard)` 之前显式 `find_package(Qt6Qml/Qt6Quick/KF6Service)`（并提供 qtdeclarative/kservice 直接依赖） |
| 4 | `ksystemstats_plugin_cpu` 链接失败：`target_link_libraries` 签名混用 | 上游该目标用 plain 签名，我新增的调用用了 PRIVATE | 0003：新增调用改回 plain 签名 |
| 5 | `libdrm/i915_drm.h` 找不到 | Intel helper 目标没有任何 include；该头位于 `<libdrm 包>/include/libdrm/`，不在默认搜索路径 | 0009：`find_path(LIBDRM_INCLUDE_DIR NAMES libdrm/i915_drm.h)` 后显式加 include |
| 6 | `std::ranges::transform` 不存在 | OHOS SDK libc++（clang 15）ranges 算法集不全（libksysguard 0005 同因） | 0010：改写为经典 `std::transform`，语义不变 |
| 7 | `redefinition of 'sockaddr_storage'` | bionic `sys/socket.h` 仅在 `__MUSL__` 下引入 `linux/socket.h`，否则自带该结构；libnl 又会拉入内核头 | 0015：E091 模式的中性守卫——先解析 libc 头，再在 `#include <linux/socket.h>` 周围用 `#if defined(__linux__) && !defined(__GLIBC__)` 重命名内核侧定义（不含 `__OHOS__`，PF5 合规） |
| 8 | `disks.cpp` 报 `const QStorageInfo (QString)` 不是结构体 | 最烦琐解析（most vexing parse） | 0008：先把路径绑定到具名变量再构造 `QStorageInfo` |
| 9 | TestLinuxCpu 编译失败：缺 `KLocalizedString` / `sensors/sensors.h` | 该 autotest 直接编译插件源文件，但没有继承插件的私有依赖 | 0004：为测试目标补 KF6::I18n 与（启用时）lm-sensors 的 include/lib |
| 10 | `undefined symbol: KSysGuard::makeSensorsFeatureSensor` | **已发布 libksysguard/6.7.2 未启用 lm-sensors**：其 `systemstats/CMakeLists.txt` 把 `SensorsFeatureSensor.cpp` 放在 `if(SENSORS_FOUND)` 内，而头文件在裸 `#ifdef Q_OS_LINUX` 下无条件声明该函数 | 见下节「lm-sensors 决策」 |
| 11 | 上游 ctest 运行期 `Error loading shared library ../bin/libKSysGuardFormatter.so` 与 `~/.cache/conan2/...` 绝对路径 | 已发布 libksysguard 的 ELF 记录了两类带斜杠的 DT_NEEDED：绝对路径指向构建机的旧 Conan cache 前缀 `~/.cache/conan2`，以及相对路径 `../bin/libKSysGuardFormatter.so`（加载器对含 `/` 的 NEEDED 一律按原样解析，不走 LD_LIBRARY_PATH） | 配方 `_bridge_legacy_needed_paths()`：把旧前缀目录 symlink 到活动缓存，并在每个 ctest 工作目录物化相对链接（E537；akonadi/baloo 先例） |
| 12 | `ksystemstatstest` SIGSEGV（访问 0x60） | `libQt6DBus` 用 `QLibrary("libdbus-1")` **运行期**加载 dbus 客户端，制品仓只有**静态** `libdbus-1.a` → 加载失败，`QDBusConnection::sessionBus()` 返回未连接对象（`isConnected()==false`）→ QtDBus 无空值保护崩溃 | 复刻 kglobalacceld 方案：`source()` 取官方 dbus 1.14.10 源码，`build()` 编译共享 `libdbus-1.so`，纳入运行期 `LD_LIBRARY_PATH` 并随包安装到 `lib/` |
| 13 | 打包后的守护进程 `No plugins found` | KDEInstallDirs 把插件装到 `<prefix>/lib/plugins`，而 `package_info` 里写的是 `<prefix>/plugins` | 修正 runenv `QT_PLUGIN_PATH` 为 `lib/plugins` |
| 14 | `--print-address` 读不到总线地址 | 重定向到文件的 stdout 是块缓冲，地址迟迟不落地（`--print-address=3` 在 conan 的 shell 包装下 fd 不可用） | 消费端测试改用 `dbus-run-session --config-file=<tcp conf>` 自行启动并导出地址，脚本在其内部 re-exec |

## lm-sensors 决策（R36 情形）

**事实链（均有实证）**

1. 上游顶层在 Linux 分支 `find_package(Sensors)`（TYPE REQUIRED），其消费点为
   `src/daemon.cpp`（`sensors_init/sensors_cleanup`）、`plugins/cpu`（核心温度）、
   `plugins/gpu/LinuxAmdGpu.cpp`（AMD 温度）、`plugins/lmsensors`（插件本体）。
2. 这四处都调用 `KSysGuard::makeSensorsFeatureSensor`。
3. 已发布 `libksysguard/6.7.2` 的 5 个库中该符号数量为 **0**（`readelf -sW --dyn-syms` 全扫）：
   其 `systemstats/CMakeLists.txt` 用 `if (SENSORS_FOUND)` 门控 `SensorsFeatureSensor.cpp`，
   而该配方未声明 lm-sensors。
4. 因此在本平台「启用 lm-sensors」与「链接已发布 libksysguard」**不可兼得**。
   强制覆盖版本会级联冲突（kpackage/6.18.0.1 → karchive/6.18.0 …）并迫使 libksysguard
   放弃预编译包从源码重建。

**决策（经用户确认，方案 A）**：与已发布依赖对齐，**不启用 lm-sensors**。

- 配方不声明 `lm-sensors`；顶层在其缺位时 `SENSORS_FOUND=false`，
  并把 `Sensors` 从 REQUIRED 降为 RECOMMENDED（否则 `feature_summary` 致命）。
- 新增 `KSYSTEMSTATS_WITH_LM_SENSORS` 开关与 `HAVE_SENSORS` 编译定义，
  把四处 sensors 用法改为与 libksysguard 自身相同的 `SENSORS_FOUND` 语义。
- **功能影响（如实记录）**：CPU/AMD GPU 温度传感器与 lmsensors 插件不构建；
  CPU 使用率/频率、内存、磁盘、网络（rtnetlink）、压力（PSI）、电源、osinfo、
  GPU 设备枚举、kstatsviewer 与全部 3 个上游测试均正常。
- **恢复路径**：先按 R36/R37 把 libksysguard 加 `lm-sensors` 并递增发布为
  `libksysguard/6.7.2.1`（单独 PR），再在本包 `requires` 中改引用并
  置 `KSYSTEMSTATS_WITH_LM_SENSORS=ON` 即可恢复全部温度功能。

## 源码修改（patches/，17 个）

- `0001-CMakeLists.txt.patch`：Linux-like 平台变量、
  KF6 下限 6.18、KIO 可选、KSysGuard 链接接口组件预导入。
- `0002` / `0003` / `0013` / `0014`：pressure、cpu、memory、network（rtnetlink）
  各门控并入 Linux-like 平台。
- `0004`：注册 TestLinuxCpu 并补其私有依赖（KF6::I18n、lm-sensors 条件）。
- `0005` / `0006` / `0011` / `0017`：sensors API 用法统一改为 `HAVE_SENSORS` 门控
  （CPU 温度、CPU hwmon 发现、AMD GPU 温度、daemon 的 sensors 初始化/清理）。
- `0007` / `0008`：disks 插件 KIO 可选 + `QStorageInfo` 等价回退（含最烦琐解析修复）。
- `0009`：GPU 的 Linux 后端并入 Linux-like 平台、libdrm include 定位、lm-sensors 路径。
- `0010`：Intel helper 的 `std::ranges::transform` → 经典算法。
- `0012` / `0016`：lmsensors 插件与 daemon core 的 lm-sensors include/lib 接线。
- `0015`：非 glibc Linux 上 `linux/socket.h` 与 libc 的 `sockaddr_storage` 冲突守卫。

全部补丁只在 Linux-like 平台生效或不改变非 Linux 平台行为；未在 `patches/` 中引入
平台宏（`HAVE_SENSORS`/`KSYSTEMSTATS_USE_KIO`/`KSYSTEMSTATS_WITH_LM_SENSORS`
均为中立特性开关，符合 R8 与 PF5）。

> **补丁命名与重生成注意**：本目录的补丁由 `ohc-run.py refresh-patch --auto`
> 按 `{seq}-{源文件名}.patch` 生成，并与 `conandata.yml` 的 `patches` 列表及
> 本文件 `manifest.yaml` 的 `patches_applied` **保持同名一致**。
> 每次执行 `refresh-patch`（`finish`/`submit` 内部也会调用）后，必须：
> ①清理 `patches/.patch-backup-*` 与 `.patch-staging`；
> ②核对实际文件名与 `conandata.yml` 完全一致（含顺序）；
> ③删除 `refresh-patch` 写入 manifest.yaml 的 `patch_generation`
> （含构建机绝对路径）与 `patch_classification`（`guard: pending` 占位）段——
> 仓库内已合并包均不保留这两段。
>
> 已验证（本轮交付前）：17 个补丁按 `conandata.yml` 顺序以 `patch -p1` 干净应用，
> 且应用结果与生成时的工作树逐文件一致。

## 依赖版本（已发布 ohpcd refs，全缓存命中）

- qtbase/6.11.1.1（`override=True`，FEATURE_dbus=ON；libksysguard 前例）、
  qtdeclarative/6.11.1（Qt6Qml/Qt6Quick）、kservice/6.18.0（KF6::Service）
- kcoreaddons/6.18.0、kcrash/6.18.0、solid/6.26.0
- libksysguard/6.7.2（package_id `5e999d5d…` 与发布版一致，Download 命中）
- libnl/3.11.0（NL）、eudev/3.2.14（UDev，配方显式声明 `UDev::UDev` 目标名）、
  libdrm/2.4.133（Intel helper 头文件）
- ecm/6.26.0（tool_requires）、dbus/1.14.10.1（tool_requires，提供 dbus-daemon
  与 dbus-run-session）

## 验证结果（实测）

```bash
# conan create（W3 全量，--build=ksystemstats/6.7.2）：EXIT=0
# ── 上游 CTest：3/3 可执行文件 / 8/8 测试函数 通过（100%）──
1/3 TestLinuxCpu ......... Passed
2/3 nvidiatest ........... Passed
3/3 ksystemstatstest ..... Passed
#   测试函数粒度共 8 个，全部 PASS：
#   ksystemstatstest 6 个：initTestCase / findById / update / subscription / changes / dbusApi
#   TestLinuxCpu 1 个：testParseCpuinfo（4 行数据）
#   nvidiatest 1 个：testDmonParsing（3 行数据）
#   （dbusApi 通过 D-Bus 自调用验证 allSensors/sensorData/subscribe/newSensorData）

# ── 消费端 test_package：PASS ──
session bus: tcp:host=127.0.0.1,port=...            # dbus-run-session 私有总线
PASS: packaged daemon published 274 sensors; cpu/all/usage reported a live value
#   断言容器：cpu / memory / disk / network / os / power / pressure / gpu
#   （全部由打包插件无条件创建；cpu/all/usage 返回实时值）
```

## 修复轮次与止损

- 编译/链接修复共 6 轮（KIO→平台门控→KSysGuard 目标→链接签名→libdrm→ranges→
  sockaddr_storage→最烦琐解析→autotest 依赖），每轮均以实际报错定位，未做无证据调参（R43）。
- 运行期修复 3 轮（DT_NEEDED 桥接 → libdbus 共享库 → 插件路径/总线启动），
  均通过 `dbus-run-session` + 真实传感器列表验证，未使用豁免或跳过。
- 上游测试**零豁免、零排除**：8/8 QTest 测试函数（3/3 CTest 可执行文件）全通过，路径 A 通过率 100%。
---

**编译结束**: 2026-09-27 17:18
**最终状态**: built
