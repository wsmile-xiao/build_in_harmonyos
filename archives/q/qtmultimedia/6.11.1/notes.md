# qtmultimedia 6.11.1 适配笔记

## 基本信息

- 软件名称: qtmultimedia（Qt Multimedia 模块）
- 版本: 6.11.1
- 构建系统: cmake
- 编译日期: 2026-08-12
- 状态: published
- 上游仓库: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtmultimedia-everywhere-src-6.11.1.tar.xz
- 适配路径: 路径 A（基础适配）

## 编译步骤

1. `ohc-run.py init-build qtmultimedia 6.11.1 --url=https://mirrors.tuna.tsinghua.edu.cn/qt/official_releases/qt/6.11/6.11.1/submodules/qtmultimedia-everywhere-src-6.11.1.tar.xz`
2. CMake 配置（conan create 内部）：`QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`、`Qt6_DIR=<qtbase 包>/lib/cmake/Qt6`、`Qt6ShaderTools_DIR=<qtshadertools 包>/lib/cmake/Qt6ShaderTools`
3. `cmake --build --parallel 4` 生成 libQt6Multimedia.so / libQt6MultimediaWidgets.so / libQt6SpatialAudio.so（并行编译以压缩 W3 本地 CI 600s 窗口，参考 openssl 先例）
4. ctest -R 运行 18 个可在 OHOS 运行的 unit 测试（18/18 通过）
5. `conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全部通过

## 依赖

- qtbase/6.11.1（Core/Gui REQUIRED，提供 Qt6Config.cmake 与 harmonyos-clang mkspec）
- qtshadertools/6.11.1（提供 qt_internal_add_shaders CMake 宏与 qsb 宿主工具）

## 关键适配点

1. **Qt6ShaderTools_DIR 必需**：qtmultimedia 的 src/multimedia 用 `qt_internal_add_shaders` 预编译 shader，必须在 CMakeToolchain 显式设置 `Qt6ShaderTools_DIR` 指向 qtshadertools 包 lib/cmake/Qt6ShaderTools，否则 configure 报 `Unknown CMake command "qt_internal_add_shaders"`。
2. **qsb 宿主工具 LD_LIBRARY_PATH**：Qt Shader Baker（qsb）构建期运行预编译 shader，需要 LD_LIBRARY_PATH 指向 qtbase/qtshadertools 包 lib；配方 build() 用 `cmake -E env LD_LIBRARY_PATH=... cmake --build` 注入。
3. **memory_resource 头缺失**：OHOS libc++ 不提供标准 `<memory_resource>`，qmemory_resource_tlsf.cpp 改为复用 QtMultimediaPrivate::pmr emulation（q_pmr_emulation_p.h 提供），补丁 0001。
4. **无媒体后端**：OHOS 无音频/视频后端（configure 报 No backend），40 个 integration/backend 测试需真实设备，MANIFEST.yml 声明排除；ctest -R 只运行 18 个可运行 unit 测试。
5. **并行编译**：`--parallel 4` 压缩编译时间至 W3 600s 窗口内（参考 openssl make -j2 先例）。

## 验证结果

- conan create 干净构建通过（G2）
- 上游 unit 测试: 18/18 通过（100%）
- test_package 消费者测试（QMediaPlayer/QMediaDevices/QMediaMetaData 6 条断言）: ALL PASSED
- conan-verify: G0-G4 全 PASS
- W3 本地 CI 模拟（build_and_test.sh）: L0/L1/L2/L4/L5 全 PASS，Pass rate 100%
- pre_pr_audit W4 审计: P0=0, P1=0（P2/P3 警告已处理）

## 最终状态

built → published（conan-verify 通过 + finish W3 通过）

## 编译结束

qtmultimedia 6.11.1 适配完成：conan-verify G0-G4 全 PASS，上游 18/18 unit 测试通过，test_package 消费者测试 ALL PASSED，W3 本地 CI 模拟 100% 通过。
