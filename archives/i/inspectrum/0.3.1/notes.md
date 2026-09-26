# inspectrum 0.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang/clang++ (OHOS aarch64 交叉编译)
- 状态: built

## 编译步骤

conan create 全流程（conanfile.py 内 CMake configure/build/install，
日志绑定见配方 `_cmake_step`）。无源码补丁、无平台宏。

## 上游测试清点（R51 申报表）

| 项 | 结果 |
|----|------|
| 上游测试框架 | CMake enable_testing() 已声明，但无实际测试 |
| add_test() 注册数 | 0（`grep -rn add_test` 全树 0 命中） |
| tests/ 目录 | 不存在（`find . -iname "*test*"` 仅命中 CMakeLists 内 enable_testing 字样） |
| ctest 注册数 | 0 |
| 结论 | **上游确无测试**（附清点证据），等价验证由 test_package 消费者测试承担：C++ 消费者测试（FFTW 实算 8 点 FFT + liquid 滤波器系数与执行 + Qt 运行时初始化）+ 打包二进制限时启动冒烟（offscreen 平台） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游下载 404 | 上游 tag 带 v 前缀（v0.3.1） | conandata.yml 指向 tags/v0.3.1 |
| 2 | 依赖选型 | 制品仓 fftw/3.3.11 只含双精度 fftw3；上游 FindFFTW 找的是 fftw3f（单精度） | 依赖 fftw3f/3.3.10（制品仓已发布） |
| 3 | liquid-dsp 链接形态 | liquid-dsp/1.8.2 发布的是静态 libliquid.a | 配方按 .so/.a 存在性自适应取路径 |
| 4 | Find 模块适配 | 上游自带 FindFFTW/FindLiquid 自定义模块 | 模块尊重预设缓存变量，直接传 FFTW_INCLUDES/FFTW_LIBRARIES/LIQUID_INCLUDES/LIQUID_LIBRARIES 绝对路径，无需补丁 |
| 5 | Qt5 配置脏路径 | 制品仓 qtbase 包 Qt5CoreConfigExtrasMkspecDir.cmake 硬编码构建机路径 | generate() 动态改写为包内路径（neovim-qt 0.2.19 先例） |

## 源码修改

无补丁（patches/ 为空）。OHOS 适配全部在 conanfile.py 内完成。

## 依赖版本

- qt5-qtbase/5.15.2.2（Qt5Core/Gui/Widgets/Concurrent）
- fftw3f/3.3.10（单精度 FFTW，libfftw3f.so）
- liquid-dsp/1.8.2（libliquid.a，静态）

## 验证结果

- conan create 通过；test_package 消费者测试通过（QT_QPA_PLATFORM=offscreen）。
- 打包二进制限时启动冒烟通过：offscreen 平台下进程存活满 15s 无崩溃，
  日志含 QApplication/offscreen 平台插件完整初始化证据
  （QFontDatabase/QStandardPaths 输出）。
- 上游测试用例通过率: 0/0（上游无测试，不适用）。
- 新增测试用例通过率: 见 reports/test-report.md。

## 注意事项

- inspectrum 是 GUI 程序，OHOS 无显示服务器；任何自动化调用须设
  QT_QPA_PLATFORM=offscreen。**GUI 程序构造 MainWindow 后进入 Qt 事件
  循环、headless 下不会自行退出（实测 offscreen 下持续空转），冒烟验证
  必须限时（Popen + timeout kill），不能等待进程自然退出**。
- 产物为单个可执行文件 bin/inspectrum（package_type=application），
  软件级 commands.json 已建。
---

**编译结束**: 2026-09-23 21:55
**最终状态**: built
