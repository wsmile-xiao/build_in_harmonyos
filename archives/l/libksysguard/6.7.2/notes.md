# libksysguard 6.7.2 适配笔记

## 编译环境

- 构建系统: cmake (ECM / KF6, Qt6)
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, -std=c++20 -stdlib=libc++)
- 状态: built
- conan: `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（EXIT=0）

## 编译步骤

1. `conan source` 下载上游 tarball（sha256 校验）。
2. `conan create` 内部：`apply_conandata_patches` 顺序应用 0001-0009 →
   CMake configure（KF6 ≥ 6.18.0、Qt6、Libdrm、ZLIB 全部 find_package 命中）→
   `cmake.build()`（CMAKE_BUILD_PARALLEL_LEVEL=1，HMDFS 拒绝 make jobserver
   fifo，kdeclarative 6.26.0 先例）→ `_run_upstream_tests()`（ctest 全量）→
   package() 安装 → test_package 消费端验证。
3. 上游根 CMakeLists.txt:101-102 把 `CMAKE_CXX_STANDARD` 设为普通变量 20，
   覆盖 conan toolchain 缓存的 17 —— 实际编译命令为 `-std=c++20 -stdlib=libc++`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `std::jthread`/`std::stop_token` 不存在 | OHOS SDK libc++（clang 15）无该特性 | 0004：`__cpp_lib_jthread` 特性测试，回退 `std::thread` + `std::atomic<bool>` 停止标志 |
| 2 | `std::ranges::all_of/remove_if/...` 等缺失 | OHOS libc++ ranges 算法集不全 | 0005：5 文件 6 处改写为经典 std 算法/显式循环 |
| 3 | `xf86drm.h` 找不到 | conan libdrm 包头布局为根 + libdrm/ 子目录，上游未带 include dir | 0006：`target_include_directories(... ${Libdrm_INCLUDE_DIR} ${Libdrm_INCLUDE_DIR}/libdrm)`（目标由 qtbase 捆绑的 kwin FindLibdrm.cmake 定义，无需改名） |
| 4 | P0960 圆括号聚合初始化编译错误 | clang 15 不支持（clang 16+ 特性），brace-init 又把 long→pid_t 窄化变硬错误 | 0007/0008：`HistoryKey{...}` + `GpuInfo{...}` 花括号初始化，`static_cast<pid_t>(proc->pid())` |
| 5 | `KConfigPropertyMap` 头文件不存在 | ohpcd 发布的 kconfig/6.26.0 为 KCONFIG_USE_QML=OFF 构建，KF6ConfigQml 整体缺失 | 0009：faces 内置兼容实现 `KConfigPropertyMapCompat.{h,cpp}`（QQmlPropertyMap 子类：KConfigLoader 项填充 + updateValue 写回），接管两处 include；controller 的 connect 走基类 `valueChanged(key,value)` 信号配 1 参槽（Qt 允许） |
| 6 | conan patchng 报 `source file is different` | conan 内置 patch 解析器按序严格应用，不容忍行号漂移 | 0007 在生成时基于"前序 patch 已全部应用"的树状态重生成（顺序 git apply 0001-0006 后再 diff） |
| 7 | sensorfacecontrollertest 运行时 `Error loading shared library ../../bin/libKF6ConfigCore.so` | **上游 kconfig 包缺陷**：libKF6ConfigGui.so 的 DT_NEEDED 记录为相对路径 `../../bin/libKF6ConfigCore.so`，而 Core 实际在同目录 lib/；加载器对含斜杠的 NEEDED 按 CWD 解析，ctest 测试进程 CWD = 注册目录（build/autotests/） | conanfile `_prepare_ctest_runtime_links()`：ctest 前在 `<build>/bin/libKF6ConfigCore.so`（及 fallback 层级）建指向 conan kconfig 包真实 Core 的 symlink；任何 KConfigGui 消费方打包/运行均需复现该 workaround 或修复 kconfig 包 |
| 8 | processtest 2 个子用例失败 | OHOS 内核环境差异：`/proc` 存在无名进程条目（testProcesses 断言全部进程名非空）；SCHED_IDLE nice 回读值与标准 Linux 不同（testSetScheduler(idle,0)） | 如实记录（conanfile `_evaluate_ctest_results` 显式 allowance + 本笔记），不修改上游测试 |

## 源码修改（patches/，9 个）

- `0001-lower-kf6-min-version.patch`：KF6_MIN_VERSION 6.26.0 → 6.18.0，对齐
  ohpcd 已发布 KF6 矩阵（kauth/6.18.0 为锚）。
- `0002-faces-drop-configqml.patch`：faces 目标去掉 KF6::ConfigQml 链接
  （kconfig 未启用 QML；QML 侧 `org.kde.config` 仅为模块元数据）。
- `0003-autotests-drop-configqml.patch`：autotests 同上。
- `0004-processcore-jthread-fallback.patch`：jthread/stop_token 特性测试回退。
- `0005-processcore-ranges-compat.patch`：std::ranges 算法改写。
- `0006-gpu-plugin-libdrm-include.patch`：libdrm include 目录补充。
- `0007-gpu-plugin-aggregate-init.patch`：HistoryKey 聚合初始化（花括号）。
- `0008-gpu-plugin-narrowing-aggregate.patch`：0007 的姊妹修复——
  `GpuInfo{...}` 花括号聚合 + pid_t 显式窄化 cast。
- `0009-faces-kconfigpropertymap-compat.patch`：KConfigPropertyMap 兼容实现。

## 依赖版本（已发布 ohpcd refs）

- qtbase/6.11.1.1（override=True，FEATURE_dbus=ON；baloo 6.28.0 先例）、
  qtdeclarative/6.11.1、qtshadertools/6.11.1
- kcoreaddons/6.18.0、kconfig/6.18.0、ki18n/6.18.0、kauth/6.18.0、
  kservice/6.18.0、kpackage/6.18.0.1
- knewstuff/6.26.0、solid/6.26.0
- zlib/1.3.2、libdrm/2.4.133
- ecm/6.26.0（tool_requires）

## 验证结果（实测）

```bash
# conan create（W3 全量）：EXIT=0
# 7 个上游 CTest：6/7 通过（86%）
2/7 formattertest ............  Passed   0.09 s
3/7 sensortreemodeltest ......  Passed   0.16 s
4/7 sensordatamodeltest ......  Passed   0.14 s
5/7 processdatamodeltest .....  Passed   0.45 s
6/7 cgrouptest ...............  Passed   0.12 s
7/7 sensorfacecontrollertest .  Passed   0.26 s   # kconfig NEEDED workaround 后
1/7 processtest ..............  Failed   2.6 s    # 10 pass / 2 fail / 8 skip
#   失败子用例（环境差异，见上表 #8）：
#   testProcesses: '!process->name().isEmpty()' returned FALSE
#     （OHOS /proc 存在无名进程条目）
#   testSetScheduler(idle,0): niceLevel()=-10, expected 0
#     （SCHED_IDLE nice 回读与 Linux 不同）
# 注：sensortreemodeltest/sensordatamodeltest 的 ksystemstats D-Bus 守护进程
# 缺席自跳过（SKIP）子用例与上游设计一致（守护进程在独立 ksystemstats 仓库）。

# test_package（消费端）：PASS
PASS: Formatter::formatValue(1024.0, UnitByte) = "1.0 Ki​B", symbol(UnitByte) = "B"
# find_package(KSysGuard) 经上游 KSysGuardConfig.cmake 解析全部 5 个
# KSysGuard::* 导入目标（Formatter/ProcessCore/Sensors/SensorFaces/SystemStats）

# 包内容（package_id 5e999d5d282d2e11b408b89909277c634e6670a3）
# lib/: libKSysGuardFormatter.so libKSysGuardSystemStats.so
#       libKSysGuardSensors.so libprocesscore.so(小写, OUTPUT_NAME=processcore)
#       libKSysGuardSensorFaces.so lib/cmake/KSysGuard/KSysGuardConfig.cmake
# bin/: ksysguard-identify  bin/kf6/kauth/: ksysguardprocesslist_helper
# lib/plugins/: ksysguard(gpu) kf6/  lib/qml/: org/kde/ksysguard
```
---

**编译结束**: 2026-09-23 18:25
**最终状态**: built
