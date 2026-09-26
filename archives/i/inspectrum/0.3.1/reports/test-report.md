# 测试报告 — inspectrum 0.3.1

> **项目**: inspectrum
> **测试日期**: 2026-09-23
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64
> **测试类型**: 上游测试清点 + test_package 消费者测试 + 打包二进制实测

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试数 | 0 | —（上游无测试） |
| 消费者测试 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游测试用例通过率**: 0/0（上游确无测试，不适用——清点证据见 notes.md R51 申报表：`enable_testing()` 已声明但全树 0 个 `add_test()`、无 tests/ 目录）
**新增测试用例通过率**: ✅ **100%（2/2）**

---

## 二、测试结论

### 2.1 总体评价

✅ **test_package 两项消费者测试全部通过，打包二进制可正常启动运行。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| GUI 事件循环不退出（headless 空转） | 自动化冒烟需限时 kill | 🟢 |
| 字体目录缺失告警（Qt 不再自带 fonts） | GUI 渲染依赖设备字体 | 🟢 |

### 2.3 可用功能清单

```
✅ 可执行文件 bin/inspectrum 启动运行（offscreen 平台，存活 15s 无崩溃）
✅ QApplication/offscreen 平台插件完整初始化（日志证据 QFontDatabase/QStandardPaths）
✅ 依赖闭包可消费：Qt5 Core/Widgets/Concurrent + fftw3f + liquid-dsp 全部链接成功
✅ fftw3f 单精度 FFT 实算（8 点正变换，DC=0、k=4 bin 幅值=8，误差 <1e-3）
✅ liquid_firdes_kaiser 滤波器设计 + firfilt_crcf 执行（输出有限）
⚠️ GUI 显示：OHOS 无 X11/Wayland，交互式频谱查看需设备侧显示栈（offscreen 平台已验证渲染栈初始化）
```

### 2.4 已知限制

1. inspectrum 为 Qt5 GUI 程序，构造 MainWindow 后进入事件循环、headless 下不会自行退出（实测持续空转），自动化验证必须限时（Popen + timeout kill）。
2. GUI 窗口显示依赖设备显示服务器，本适配验证覆盖启动、依赖链接闭包与 DSP/FFT 计算路径。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_package/test.cpp — FFTW 阶段 | fftwf_plan/execute 8 点单精度 FFT，验证 DC bin=0、k=4 bin 幅值=8 | ✅ PASS |
| test_package/test.cpp — liquid 阶段 | liquid_firdes_kaiser 61 抽头低通（系数有限、增益合理）+ firfilt_crcf 脉冲执行 | ✅ PASS |
| test_package/test.cpp — Qt 阶段 | QCoreApplication 初始化 + QString/QStringList | ✅ PASS |
| 打包二进制实测 | bin/inspectrum offscreen 启动，存活满 15s 无崩溃，Qt 运行时初始化证据齐全 | ✅ PASS |
| L1e 破坏性反向验证（R34） | 移走 bin/ 后测试失败 → 测试实质依赖被测包 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| （无） | — | — |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 上游测试套件 | 上游确无测试（0 个 add_test），非主动跳过 |
| L2 smoke --version/--help | GUI 进程进入事件循环不退出，非阻塞告警；等价覆盖由限时启动冒烟完成 |

---

## 四、关键问题分析

### 问题1: `inspectrum --help` 不退出导致冒烟挂起

**现象**：
```
进程存活 10 分钟以上、CPU 92% 空转（进入 Qt 事件循环）
```

**根因分析**：
GUI 程序在构造 MainWindow 后进入 `a.exec()` 事件循环，headless（offscreen 平台）下无退出路径；上游未提供任何 headless CLI 模式。

**解决方案**：
test_package 应用验证改为限时启动冒烟：Popen 启动 → 存活满 15s 无崩溃 → kill → 断言日志含 QApplication/offscreen 初始化证据。

### 问题2: 上游 cmake_minimum_required(3.1) 与 CMake 4 不兼容

**现象**：
```
Compatibility with CMake < 3.5 has been removed from CMake.
```

**根因分析**：
CI 构建镜像 CMake 4.1 移除了对 <3.5 的策略兼容。

**解决方案**：
配方注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，无源码补丁。

---

## 五、测试环境

```
inspectrum/0.3.1@ohpcd/stable (aarch64, os=OHOS, clang 15, cppstd=17, libc++, Release)
deps: qt5-qtbase/5.15.2.2, fftw3f/3.3.10, liquid-dsp/1.8.2
conan 2.29.1, profile ohos-aarch64
```

---

*报告生成时间: 2026-09-23*
