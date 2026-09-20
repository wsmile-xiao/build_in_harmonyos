# vibes - HarmonyOS 编译记录

## 概述

**VIBES**（**V**Isualizer for **I**ntervals and **B**oxES）是一个面向区间方法（interval methods）可视化的开源科学可视化系统，由两部分组成：

- **VIBES 查看器应用**（`viewer/`）：Qt5/Qt6 GUI 桌面应用，负责查看、标注与导出图形。
- **VIBES 客户端 API**（`client-api/`）：提供 C、C++、Python、MATLAB 等语言的轻量客户端库，用于向查看器发送 JSON 绘图命令。

本仓库适配打包的是 **C++ 客户端 API**（`client-api/C++`）：单翻译单元 `vibes.cpp` + 头文件 `vibes.h`，生成 `libvibes`。下游使用者链接该库，通过 `beginDrawing(file)` + 各种绘图命令把 JSON 消息写入文件（查看器是独立进程监听该文件），从而以极其轻量的方式实现可视化，无需复杂安装与库依赖。

查看器本身是 Qt GUI 桌面应用，需要真实显示器且依赖 Qt5/Qt6 及其 SVG 模块，不适用于 OHOS headless 环境，故不包含在本配方中。

## 功能概述

- `Value` / `Params` 键值系统与 JSON 序列化（int / decimal / bool / string / array / object）
- 图元绘制：box、ellipse、circle、line、arrow、polygon、point、ring、sector、pie、vehicle、raster、text 等
- 图形/视图管理：newFigure、clearFigure、closeFigure、saveImage、axisAuto/axisEqual/axisLimits/axisLabels、showAxis
- 对象分组与属性修改：newGroup、clearGroup、removeObject、setObjectProperty/ies、setFigureProperty/ies
- 兼容 IBEX 区间类型（可选，本配方未启用）

## OHOS 适配

- **纯 C++11、零外部依赖**（仅 STL + stdio），无需补丁。
- **client-api/C++ 无上游构建系统**（只有 `examples/` 有 CMakeLists），配方以 custom build 直接编译 `vibes.cpp` 生成 `libvibes`（静态默认 / `shared=True` 共享）。
- **headless 可测**：所有绘图命令把 JSON 写入文件并 `fflush`，`beginDrawing(file)` + 绘图命令可在无查看器 GUI 的 OHOS 上端到端自测。
- **上游无自动化测试套件**（`examples/` 为无断言演示程序；`viewer/tests/all_commands.json` 是 Qt fixture），`test_package` 以真实 API 消费者断言测试（13 项）覆盖，MANIFEST.yml 含 no_tests 审计。

## 依赖关系

- **编译依赖**：无（单翻译单元，STL + libc 即可）。
- **运行依赖**：无。

## 参考资料

- 官网：https://ENSTABretagneRobotics.github.io/VIBES
- 源码仓库：https://github.com/ENSTABretagneRobotics/VIBES
- 论文：V. Drevelle, J. Nicola. "VIBES: A Visualizer for Intervals and Boxes". Mathematics in Computer Science, 8(3-4), 2014.
