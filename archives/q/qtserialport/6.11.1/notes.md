# qtserialport 6.11.1 适配笔记（HarmonyOS PC / aarch64）

## 概述

- 软件：qtserialport 6.11.1（Qt 6 串口通信模块，C++）
- 上游：https://github.com/qt/qtserialport
- 官方源码包：qtserialport-everywhere-src-6.11.1.tar.xz
  - sha256: 9af31a898ffd9a7e4faf6fed845d29e783c716885789055cbe319f3e072d3974
- 构建系统：CMake（Qt 6 模块构建，qt_internal_add_module）
- 依赖：qtbase/6.11.1（已发布到 ohpcd 制品仓，recipe 714d84d0 + binary 20.3MB）
- 产物：libQt6SerialPort.so（动态库，非命令行工具，无需 commands.json，R38）

## 适配路径

1. W0 依赖检查：`conan download qtbase/6.11.1 -r=ohpcd --only-recipe` 验证已发布；
   `conan install --requires=qtbase/6.11.1 --build=never` 验证 binary 可下载。
   preflight_check.sh 曾误报"未发布"（conan list 对 cnb.cool 制品仓返回不完整，R35）。
2. W1 同步：worktree 基于最新 main（0fc5adb9d），无需再同步。
3. init-build：下载官方 tarball 到 $TMPDIR/builds 后 init-build 完成（GitHub 直接 URL 返回 HTML，改用 download.qt.io 官方 tarball）。
4. 手动编译（探索模式）：
   ```bash
   cmake -S . -B build -DCMAKE_PREFIX_PATH=$QTPFX -DQT_HOST_PATH=$QTPFX \
     -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang \
     -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
     -DQT_BUILD_TESTS=ON -DQT_BUILD_TESTS_BY_DEFAULT=OFF
   make -j4
   make install DESTDIR=$TEST_PREFIX
   ```
   要点：Qt 6 模块交叉编译需设置 QT_HOST_PATH（本机 OHOS aarch64，host=target 同一前缀）。
5. conan-init 生成配方后人工改写为 CMake 模板（conan-init 误判 autotools）。
6. conan-verify 验证（G0-G4 + L2/L4/L5）。

## 编译结果

- configure：通过（CMake 3.16+，harmonyos-clang mkspec）
- make：通过，产出 `lib/libQt6SerialPort.so`（.so.6 -> .so.6.11.1）
- make install：通过（头文件 include/QtSerialPort、CMake 包 lib/cmake/Qt6SerialPort、mkspecs、pkgconfig、SBOM）
- 测试：
  - `tst_qserialport` 通过（ctest 0.12s）
  - `tst_qserialportinfo` 通过（ctest 0.06s）
  - `module_includes` ctest 失败：测试子工程未显式传 Qt6_DIR（Qt 构建树测试环境限制）；
    手动以 `-DQt6_DIR=$QTPFX/lib/cmake/Qt6` 配置并构建 module_includes_exe 成功运行
    （下游 find_package(Qt6SerialPort) + 链接 + 执行 exit=0），证明下游可用性。

## 配方要点（conanfile.py）

- `requirements()`: `qtbase/6.11.1`
- `generate()`: CMAKE_PREFIX_PATH=qtbase 包前缀；CMAKE_MODULE_PATH=qtbase lib/cmake/Qt6/platforms
  （Platform/HarmonyOS.cmake）；QT_QMAKE_TARGET_MKSPEC=harmonyos-clang；BUILD_SHARED_LIBS；
  FEATURE_libudev=OFF（避免 udev 依赖）；QT_NO_ARM_AES_INTRINSICS（R40 平台适配）
- `build()`: cmake configure/build + 构建并运行上游测试（LD_LIBRARY_PATH 追加 qtbase lib）
- `package()`: cmake.install() + OHOS ELF 重签名（binary-sign-tool）
- `package_info()`: cmake_find_mode=none（复用 Qt 自带 Qt6SerialPortConfig.cmake）+ component serialport

## test_package

- test_qtserialport.cpp：真实调用 `QSerialPortInfo::availablePorts()` 枚举端口、
  `QSerialPort` 构造/setPortName/isOpen/error() 等 API，10 个断言（R34 非空壳测试）。

## 遇到的问题与解决

| 问题 | 解决 |
|------|------|
| GitHub URL 直接下载返回 HTML | 改用 download.qt.io 官方 tarball（--url 传官方地址） |
| `conan` 命令解析到错误 ELF（_posixsubprocess 缺失） | 创建 wrapper：hnp python3 + PYTHONPATH 指向 conans site-packages |
| CMake 报 "You need to set QT_HOST_PATH to cross compile Qt" | 设置 QT_HOST_PATH=qtbase 前缀（本机同架构） |
| ctest module_includes 缺 Qt6_DIR | 测试环境限制，手动验证下游链接 OK，记录不阻塞 |

## 知识草稿

编译过程中未出现知识图谱未覆盖的新错误模式（CMake/Qt6 相关模式已由 qtbase/qtpositioning/qtsvg 沉淀），
未生成新 DRAFT。若 conan-verify 出现新错误再补充。
---

**编译结束**: 2026-08-15 23:06
**最终状态**: built
