# 区分 KDE PIM 软件包版本与 KF6 依赖版本并核全量 CTest

> 本草稿配对 kmime/26.04.3，依据任务 13785 的 HarmonyOS PC 实测记录。

## 触发场景

KMime 使用 KDE PIM 发布版本 26.04.3，而 KF6 框架依赖使用 6.x 版本，两者是不同版本轴。该源码共注册 15 个 CTest 目标：13 个 autotests，加 `test_charfreq` 和依赖 `HAVE_GETOPT_H` 的 `test_mdn`。

## 原因机制

按包版本数字推断框架依赖版本会导致错误依赖；只统计 `autotests/` 又会漏掉 `tests/` 下的两个 CTest 目标。条件目标是否实际生成，应以目标设备完整构建后的 CTest 清单和运行结果核实。

## 操作步骤

1. 按包的 CMake `find_package` 要求确定 KF6 依赖版本，不从 PIM 发布版本推导。
2. 分开统计 `autotests/CMakeLists.txt` 的 13 项和 `tests/CMakeLists.txt` 的 2 项。
3. 在 `BUILD_TESTING=ON` 下从 build root 运行完整 CTest，确认 `test_mdn` 条件成立时进入实跑。
4. 运行原生 Conan 消费者测试并调用公开 MIME API。

## 验证依据

- 上游：https://invent.kde.org/pim/kmime
- 配方：archives/k/kmime/26.04.3/conanfile.py
- 消费者测试：archives/k/kmime/26.04.3/test_package
- 上游目标统计与实跑：15 个 CTest 目标，HarmonyOS PC 实测 15/15 通过；消费者 1/1 通过。

## 适用边界

本说明仅适用于 kmime/26.04.3。后续源码版本需重新统计测试目标并核对条件目标；未生成或未运行的目标不得报告为通过。
