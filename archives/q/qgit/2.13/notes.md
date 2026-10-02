# qgit 2.13 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，Qt5 分支）
- 编译日期: 2026-09-28
- 编译器: clang（本机 aarch64 鸿蒙PC 原生构建，profile: ci/conan/profiles/ohos-aarch64）
- 状态: published

## 编译步骤

conan create 从 conandata.yml 官方 GitHub URL 获取源码，配方流程：
1. `get()` 解压源码 → `apply_conandata_patches()` 应用 0001 补丁
2. `generate()`：CMakeDeps（qt5-qtbase 设 cmake_file_name=Qt5 生成聚合 Qt5Config）+
   CMakeToolchain（显式注入 moc/uic/rcc 三个 AUTOMOC/AUTOUIC/AUTORCC 可执行路径）
3. `cmake.configure() && cmake.build()`，`cmake.install()` 到包内 bin/qgit

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qt5_wrap_ui()/qt5_add_resources() 找不到 uic/rcc | Conan CMakeDeps 生成的 Qt5 配置不导出 Qt5::uic / Qt5::rcc 可执行目标 | 开启 CMAKE_AUTOUIC/CMAKE_AUTORCC，generate() 显式设 CMAKE_AUTOUIC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE 指向 qt5-qtbase 包内 bin/uic、bin/rcc；.ui 与 .qrc 直接列入 target 源文件（补丁 0001） |
| 2 | find_package(QT NAMES Qt6 Qt5) 后 QT_VERSION_MAJOR 未定义 | NAMES 技巧依赖上游 Qt5Config.cmake 定义的 QT_VERSION_MAJOR；CMakeDeps 聚合配置无此变量 | 补丁改为显式 find_package(Qt5 5.11.0 COMPONENTS Core Gui Widgets)，并 set(QT Qt5)、set(QT_VERSION_MAJOR 5)、set(QT_VERSION ${Qt5_VERSION}) |
| 3 | test_package 冒烟测试首次运行报 "no Qt platform plugin could be initialized"（默认找 xcb） | conanrun 聚合脚本未携带 QT_QPA_PLATFORM=offscreen | test_package 在 test() 内用 Environment(scope="run") 直接 apply() 注入 QT_QPA_PLATFORM=offscreen + QT_QPA_PLATFORM_PLUGIN_PATH + HOME/XDG_RUNTIME_DIR |

## 上游测试用例清点（R51）

qgit 2.13 上游**无测试套件**：源码树无 tests/ 目录，CMakeLists.txt 无 add_test()/enable_testing()，
qbs/pro 工程亦无测试目标（清点证据见本目录 reports/ 与 test_package/MANIFEST.yml）。
因此按 R51 自行补充冒烟测试：qgit --version 与 qgit --help（QCommandLineParser 在 GUI
事件循环前处理，offscreen 无头可跑），**通过率 2/2 = 100%**。

## 依赖版本

- qt5-qtbase/5.15.2.2（含传递依赖 zlib/1.3.1、dbus/1.14.10、expat/2.8.2，均已在制品仓发布）
- 运行时依赖系统 PATH 中的 git（冒烟测试不需要）

## 验证结果

```bash
$ qgit --version
QGit 2.13
$ qgit --help
QGit, a Git GUI viewer ...（帮助文本正常输出）
conan-verify: G0-G4 / L2 / L4 / L5 全部 PASS
```

## 注意事项

- qgit 为 GUI 应用，正常使用需要显示服务与 git；CI 冒烟测试仅验证 --version/--help
- qt5-qtbase 的 platform 插件可用集合为 minimal/offscreen/vnc（无 xcb）
- 本机/CI 的 build_and_test.sh 会在构建期向 conandata.yml 注入 gh-proxy.com 镜像回退，退出 trap 还原的是注入后副本（实测 2026-09-28：CI 结束后工作区仍为镜像形态）。**提交前必须确认 conandata.yml 只含官方 URL**（PF7/R39 硬闸），本次已因此被 atomgit-bot 判 P1 阻塞并修正。
- QT_VERSION_CHECK 拼写（应为 QT_VERSION_CHECK 宏误用）是上游原有写法，预处理下无副作用，未修改

---
**编译结束**: 2026-09-28 18:31
**最终状态**: published
