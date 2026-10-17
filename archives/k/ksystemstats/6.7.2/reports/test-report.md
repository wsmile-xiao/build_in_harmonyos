# Test Report — ksystemstats 6.7.2 (OHOS aarch64)

> **项目**: ksystemstats 6.7.2
> **测试日期**: 2026-09-27
> **测试环境**: HarmonyOS HongMeng Kernel (OHOS 6.0) aarch64，clang 15.0.4，libc++，-std=c++20
> **测试类型**: 上游官方测试套件（CTest）+ 鸿蒙消费者端到端（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试总数（QTest 测试函数） | 8 | 100% |
| 通过 (PASS) | 8 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 豁免 (ALLOWANCE) | 0 | — |

> 计数口径：**测试函数粒度**。3 个 CTest 可执行文件（`ksystemstatstest` / `TestLinuxCpu` / `nvidiatest`）共 8 个 QTest 测试函数；`*_data()` 数据供给函数不单独计数。可执行文件粒度为 3/3。

**核心功能通过率**: ✅ **100%**（8/8 测试函数，3/3 可执行文件，零豁免、零排除）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** —— 上游三个 CTest 可执行文件共 8 个 QTest 测试函数全部注册并实际运行且全部通过；消费端验证确认打包后的守护进程可发布真实传感器数据。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| lm-sensors 温度传感器未启用（依赖侧配置缺口） | CPU / AMD GPU 温度传感器与 lmsensors 插件 | 🟡 |
| 已发布 libksysguard 的 legacy DT_NEEDED | 运行时加载（已在配方/test_package 内桥接） | 🟢 |
| L4 扫描器误报（`gets` 命中 `targets` 词尾） | 仅告警展示，无实际风险 | 🟢 |

### 2.3 可用功能清单

```
✅ bin/ksystemstats                : D-Bus 守护进程（org.kde.ksystemstats）正常启动并发布传感器
✅ bin/kstatsviewer                : 传感器查询 CLI（--list 列出 274 个传感器）
✅ CPU 使用率/频率（per-core + all）: 基于 /proc/stat、/proc/cpuinfo、cpufreq
✅ 内存（physical + swap + 百分比）  : 基于 /proc/meminfo
✅ 磁盘（容量/空闲/读写速率）        : Solid + QStorageInfo + /proc/diskstats
✅ 网络（rtnetlink 后端）            : wlan0 地址/速率/信号等
✅ 压力（PSI: cpu/memory/io）        : /proc/pressure/*
✅ 电源（电池）                     : Solid::Battery
✅ osinfo（内核/发行版/Plasma 版本）  : 系统信息
✅ GPU 设备枚举                     : udev + libdrm（Intel helper 二进制随包安装）
⚠️ CPU / AMD GPU 温度传感器          : 未构建（lm-sensors 缺口，见 2.4）
⚠️ lmsensors 插件                   : 未构建（同上）
```

### 2.4 已知限制

1. **lm-sensors 温度传感器与 lmsensors 插件未启用**。上游在 Linux 下把 lm-sensors 标为 REQUIRED 并调用 `KSysGuard::makeSensorsFeatureSensor`，但已发布的 `libksysguard/6.7.2` 未启用 lm-sensors（其 `systemstats/CMakeLists.txt` 用 `if(SENSORS_FOUND)` 门控该源文件，故不导出该符号；实测其 5 个库中符号数为 0）。本平台因此不可同时满足「启用 lm-sensors」与「链接已发布 libksysguard」。**恢复路径**：先把 libksysguard 加 lm-sensors 并递增发布为 `6.7.2.1`（单独 PR），再改本包引用并置 `KSYSTEMSTATS_WITH_LM_SENSORS=ON`。
2. **已发布 libksysguard 的两类 legacy DT_NEEDED**（旧 Conan cache 绝对路径 `~/.cache/conan2/...` 与相对路径 `../bin/libKSysGuardFormatter.so`）已在配方与 test_package 内经兼容链接桥接；上游包修复后可移除。
3. **L2 smoke test 记为 skip**：守护进程与 `kstatsviewer` 均无 `--version/--help` 版本探测入口，非阻塞。

---

## 三、测试详情

### 3.1 上游官方测试（CTest，3/3 可执行文件 · 8/8 测试函数 PASS）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `ksystemstatstest` | 真实 Daemon 的传感器查找、更新帧派发、订阅/退订引用计数、值变更传播、D-Bus API（allSensors/sensorData/subscribe/newSensorData）；6 个 QTest 函数（initTestCase/findById/update/subscription/changes/dbusApi）全部通过 | ✅ PASS（6/6 函数） |
| `TestLinuxCpu` | 解析内置 `/proc/cpuinfo` 夹具（amd64、amd64 NUMA、arm、arm 无尾换行）经 `LinuxCpuPluginPrivate`；1 个 QTest 函数（testParseCpuinfo，4 行数据） | ✅ PASS（1/1 函数） |
| `nvidiatest` | 解析内置 nvidia-smi dmon 夹具经 `NvidiaSmiProcess`；1 个 QTest 函数（testDmonParsing，3 行数据） | ✅ PASS（1/1 函数） |

```bash
# 实测（conan create 内部，私有 TCP+ANONYMOUS 会话总线）
100% tests passed, 0 tests failed out of 3
ksystemstats/6.7.2: upstream ctest results: ksystemstatstest=passed, TestLinuxCpu=passed, nvidiatest=passed
# QTest 函数级实测（Testing/Temporary/LastTest.log）：
#   LinuxCpuTest   : Totals: 6 passed, 0 failed, 0 skipped
#   NvidiaParserTest: Totals: 5 passed, 0 failed, 0 skipped
#   KStatsTest     : Totals: 7 passed, 0 failed, 0 skipped
# 上述 Totals 含 initTestCase/cleanupTestCase 与每个数据行；测试函数槽计 8 个：
#   KStatsTest 6（initTestCase/findById/update/subscription/changes/dbusApi）
#   + LinuxCpuTest 1（testParseCpuinfo）+ NvidiaParserTest 1（testDmonParsing）
```

### 3.2 消费者端到端测试（test_package，1/1 PASS）

`test_package/consumer_check.sh` 启动**打包后**的 `bin/ksystemstats`（针对私有会话总线），再用**打包后**的 `bin/kstatsviewer` 查询并断言：

| # | 断言 | 期望 | 结果 |
|---|------|------|------|
| A1 | 打包二进制存在 | `bin/ksystemstats`、`bin/kstatsviewer` 可执行 | ✅ PASS |
| A2 | 守护进程发布传感器 | `kstatsviewer --list` 输出非空且非 "No sensors available." | ✅ PASS（274 个传感器） |
| A3 | cpu 容器存在 | `^cpu(/| |$)` | ✅ PASS |
| A4 | memory 容器存在 | `^memory(/| |$)` | ✅ PASS |
| A5 | disk 容器存在 | `^disk(/| |$)` | ✅ PASS |
| A6 | network 容器存在 | `^network(/| |$)` | ✅ PASS |
| A7 | os 容器存在 | `^os(/| |$)` | ✅ PASS |
| A8 | power 容器存在 | `^power(/| |$)` | ✅ PASS |
| A9 | pressure 容器存在 | `^pressure(/| |$)` | ✅ PASS |
| A10 | gpu 容器存在 | `^gpu(/| |$)` | ✅ PASS |
| A11 | 具体传感器值经 D-Bus 回传 | `cpu/all/usage` 输出 `<name> <value>` | ✅ PASS |

```bash
PASS: packaged daemon published 274 sensors; cpu/all/usage reported a live value
```

> 该测试对被测包有实质依赖：移走包的 `bin/` 或 `lib/plugins/` 即失败（CI L1e 破坏性反向验证同路径验证通过）。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| （无） | 上游 3 个 CTest 可执行文件 / 8 个 QTest 测试函数全部执行，无跳过、无豁免 |

---

## 四、关键问题分析

### 问题1: `undefined symbol: KSysGuard::makeSensorsFeatureSensor`

**现象**：
```
ld.lld: error: undefined symbol: KSysGuard::makeSensorsFeatureSensor(QString const&, sensors_chip_name const*, sensors_feature const*, KSysGuard::SensorObject*)
```

**根因分析**：
已发布 `libksysguard/6.7.2` 的 `systemstats/CMakeLists.txt` 用 `if (SENSORS_FOUND)` 门控 `SensorsFeatureSensor.cpp`，而该配方未声明 lm-sensors，故未编译该文件；但其头文件在裸 `#ifdef Q_OS_LINUX` 下无条件声明该函数。实测其 5 个库中该符号数为 0。消费方（daemon 的 sensors 初始化、CPU 温度、AMD GPU 温度、lmsensors 插件）因此链接失败。

**解决方案**：
不声明 lm-sensors，并新增中立开关 `KSYSTEMSTATS_WITH_LM_SENSORS` / `HAVE_SENSORS`，把四处调用点改为与 libksysguard 自身相同的 `SENSORS_FOUND` 语义（补丁 0003/0008/0011/0017），配方置 `KSYSTEMSTATS_WITH_LM_SENSORS=OFF`。功能缺口与恢复路径见 2.4。

### 问题2: `QDBusConnection::sessionBus()` 不可用导致 SIGSEGV

**现象**：
```
Received signal 11 (SIGSEGV), code SEGV_MAPERR, ... accessing address 0x0000000000000060
TRACE 2 base= connected=0 addr=[tcp:host=127.0.0.1,port=...,family=ipv4,guid=...]
```

**根因分析**：
`libQt6DBus` 用 `QLibrary("libdbus-1")` 在**运行期**加载 dbus 客户端（既不记录 `dbus_*` 未定义符号，也无 `libdbus-1.so` 的 NEEDED 项，故 readelf 看不出依赖），而制品仓仅发布**静态** `libdbus-1.a` → 加载失败 → 会话总线连接无效（`isConnected()==false`、`baseService` 为空）→ QtDBus 在首次 `DBusInterface` 调用时空指针解引用崩溃。

**解决方案**：
从官方 `dbus.freedesktop.org` 1.14.10 源码（SHA256 已独立复算校验）在 `build()` 内编译共享 `libdbus-1.so`，纳入运行期 `LD_LIBRARY_PATH` 并随包安装到 `lib/`（kglobalacceld 6.7.2 先例）。

---

## 五、测试环境

```
OS          : HarmonyOS / OpenHarmony 6.0 (aarch64, HMDFS)
Compiler    : clang/clang++ 15.0.4 (/data/service/hnp/bin/clang++)
Stdlib      : libc++ (-stdlib=libc++), C++20
Build       : CMake + Ninja (GNU make jobserver mkfifo 被沙箱拒绝)
Conan       : 2.29.1（OHOS 适配版）, profile ohos-aarch64
Package id  : 041ef1b21192c73bab8d4885b12c0b17c2bfdf6d
Recipe      : conan create archives/k/ksystemstats/6.7.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --build=ksystemstats/6.7.2  → EXIT=0
```

---

*报告生成时间: 2026-09-27*
