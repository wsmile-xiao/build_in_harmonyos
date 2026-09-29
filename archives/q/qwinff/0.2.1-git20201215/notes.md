# qwinff 0.2.1-git20201215 适配笔记

## 编译环境
- 构建系统: cmake (Qt5 GUI 应用)
- 编译日期: 2026-09-28
- 编译器: clang/clang++ (OHOS aarch64, clang 15.0.4)
- 状态: published
- 源码: git 快照 17e987e7c72affb7acdc67e95aae07e4bbfe93f2（2020-12-15 前的 master 末端，
  发行版打包名 0.2.1+git20201215；上游无对应 tag，取 codeload 官方快照包）

## 编译步骤

conan create（conanfile.py: CMakeToolchain + CMakeDeps + qt5-qtbase/5.15.2.2）：
- CMAKE_SYSTEM_NAME=Linux（E092，OHOS 走 Linux 平台模块）
- CMAKE_POLICY_VERSION_MINIMUM=3.5（上游要求 CMake>=3.1，本机 CMake 4.x）
- AUTOMOC/AUTORCC/AUTOUIC 可执行文件显式指向 qt5-qtbase 包内 bin/{moc,rcc,uic}
- CMAKE_INSTALL_RPATH_USE_LINK_PATH=ON（E298，包内 bin/qwinff 定位 libQt5*.so）
- test_package 采用 CMakeDeps 聚合 Qt5Config（E299，规避 qtbase 包内真实 config 的构建期 mkspecs 路径校验）
- DATA_PATH 由补丁注入为 <package>/share/qwinff（运行期定位 constants.xml/presets.xml）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | get() 报 BadZipFile | codeload URL 无扩展名，conan 误判为 zip | source() 显式传 filename=qwinff-<ver>.tar.gz |
| 2 | find_package(Qt5Network REQUIRED) 失败 | qt5-qtbase 只导出组件 config，无独立 Qt5NetworkConfig 供 conan 聚合配置解析 | 补丁改为 find_package(Qt5 COMPONENTS Network REQUIRED)（聚合 Qt5Config 处理组件） |
| 3 | translations 需要 qttools(lrelease/lupdate) | qt5-qttools 未发布到 ohpcd 制品仓 | 补丁移除 LinguistTools 与 translations 子目录（翻译非核心功能） |
| 4 | test_package 编译无 Qt 头文件路径 | CMakeDeps 聚合 Qt5Config 的组件 include dirs 为空（qt5 为传递依赖） | test_package 显式声明 self.requires("qt5-qtbase/5.15.2.2")（直接依赖）→ 聚合 Qt5Config 的组件信息完整；再设置 cmake_file_name=Qt5 走聚合配置 |
| 4b | CI worker 报 `Qt5::Core references .../p/../b//mkspecs/linux-clang but this file does not exist` | qtbase 包内真实 Qt5CoreConfigExtrasMkspecDir.cmake 硬编码构建期路径 `<pkg>/../b//mkspecs/linux-clang`；本机构建目录仍在故可通过，CI fresh cache 无 build 目录 → 必须用聚合配置（E299） | 见 #4：test_package 不再用 Qt5_DIR 指向包内真实 config，改用 CMakeDeps 聚合 Qt5Config（无构建期路径校验） |
| 5 | testupdateinfoparser 启动找不到 xcb 插件 | 本机无窗口系统，QApplication 需平台插件 | QT_QPA_PLATFORM=offscreen 内联注入（self.run env= 会整体替换环境，改用命令前缀） |
| 6 | OpenGL 视频组件 | qmpwidget 的 QGLWidget 路径 | 无需处理：上游已有 #ifdef QT_OPENGL_LIB 守卫，不链接 Qt5::OpenGL 即自动编译非 GL 路径 |
| 7 | DBus 电源管理 | 桌面 DBus 不可用 | 上游 CMake 构建已默认使用 powermanagement-dummy.cpp，无需修改 |

## 源码修改

patches/0001-cmake-no-translations-datapath.patch：
- 顶层 CMakeLists.txt: find_package 去掉 LinguistTools；Qt5Network 独立查找改聚合组件查找
- src/CMakeLists.txt: 移除 add_subdirectory(translations)；add_definitions 增加
  -DDATA_PATH="${CMAKE_INSTALL_PREFIX}/share/qwinff"（CMake 构建缺失该宏，运行期找不到数据文件）

## 依赖版本

- qt5-qtbase/5.15.2.2（Widgets/Network，Qt5Test 供上游单测）
- ffmpeg 为运行期外部命令（converter/exepath.cpp 注册 ffmpeg/ffprobe/ffplay 路径），
  非链接依赖，不进 requires

## 上游测试（R51 三步法）

- 清点：src/tests/ 下 2 个 QtTest 单元测试（testversioncompare 3 槽、testupdateinfoparser 1 槽，
  共 17 处 QCOMPARE/QVERIFY 断言），run-tests.sh 逐目录 qmake+make+运行
- 运行：test_package 重建两个测试，QT_QPA_PLATFORM=offscreen 实测
- 结果：testversioncompare Totals 5 passed/0 failed；testupdateinfoparser Totals 3 passed/0 failed
  → 通过率 8/8 = 100%

## 验证结果

conan-verify: G0-G4 + L2/L4/L5 全部 PASS；test_package 8/8 通过（100%）。
本机完整 CI（ci/conan/setup.sh + build_and_test.sh，CI_PACKAGES=archives/q/qwinff/0.2.1-git20201215）:
L0 pass / L1 pass（含 L1e R34 破坏性负测试）/ L2 skip（GUI 应用无 version/help 输出）/
L4 warn / L5 pass，Pass rate 100% (1/1)。

CI fresh-cache 复现（E299 验证）：把 qtbase 包相邻 build 目录中的 `b/mkspecs/linux-clang`
暂时移走（模拟 CI worker 只有包、无 build 目录），再执行完整 CI 仍 100% (1/1) 通过，
证明聚合配置已生效、不依赖构建期残留路径；日志见 reports/ci-fresh-cache-emulation.log。

L4 为误报：扫描规则 `grep -E '(strcpy|sprintf|gets|strcat)\b'` 匹配到补丁上下文行中的
`Qt5::Widgets`（单词尾部含 "gets"），补丁本身不含任何危险函数调用。

## 注意事项

- GUI 应用：包内 bin/qwinff 在无窗口环境下不可直接启动 GUI（无 xcb/wayland 插件）；
  test() 以包内可执行文件存在性断言 + 上游 QtTest 单测替代 GUI 冒烟
- 运行期需要 ffmpeg/ffprobe 可执行文件在 PATH（由 ffmpeg 包或系统提供）
## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conan 包 qwinff/0.2.1-git20201215@ohpcd/stable | 1.2MB | 含 bin/qwinff + share/qwinff/{presets,constants}.xml + desktop/icon |
| packaging/qwinff-0.2.1-git20201215-ohos-aarch64.tar.gz | 1.2MB | 本地打包快照（二进制产物不入库，由 CI/发布流程生成） |
---

**编译结束**: 2026-09-28 22:31
**最终状态**: published
