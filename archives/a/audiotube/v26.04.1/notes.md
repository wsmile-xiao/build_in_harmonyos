# audiotube v26.04.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (Clang 15.0.4 for OHOS aarch64)
- 状态: built (minimal - ytm library only)

## 编译步骤

```bash
# 清理并创建build目录
rm -rf build && mkdir build

# cmake 配置（OHOS minimal build模式）
cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DOHOS_MINIMAL_BUILD=ON \
      -Dpybind11_DIR=/storage/Users/currentUser/.opendesk/interpreters/pip-global/pybind11/share/cmake/pybind11 \
      ..

# 编译
make -j2

# 安装到DESTDIR
make install DESTDIR=$TEST_PREFIX

# ctest（minimal build模式下无测试）
ctest --output-on-failure
# No tests were found
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt6Qml/Quick/QuickControls2/Multimedia 未安装 | OHOS预编译包中仅有qtbase/qtsvg/qtimageformats，缺少QML/Multimedia模块 | 添加OHOS_MINIMAL_BUILD选项，跳过QML/GUI部分 |
| 2 | KF6Kirigami/KirigamiAddons 未安装 | Kirigami是KDE QML UI框架，没有OHOS预编译包 | OHOS_MINIMAL_BUILD模式下跳过整个audiotube可执行文件构建 |
| 3 | FutureSQL6/QCoro6 未安装 | KDE异步SQL和Qt协程库，无OHOS预编译包 | OHOS_MINIMAL_BUILD模式下跳过 |
| 4 | pybind11 cmake配置不在默认路径 | 通过pip安装的pybind11在非标准路径 | 添加-Dpybind11_DIR参数指定路径 |
| 5 | Ytdlp/YTMusicAPI RUNTIME依赖缺失 | 这些是Python运行时包（pip无法在交叉编译环境安装） | OHOS_MINIMAL_BUILD模式下跳过RUNTIME依赖检查 |

## 源码修改

- 0001-CMakeLists.txt.patch: 添加OHOS_MINIMAL_BUILD选项，将QML/KF/GUI依赖改为条件性REQUIRED，跳过desktop/appdata/icon安装
- 0002-src-CMakeLists.txt.patch: 在OHOS_MINIMAL_BUILD模式下只构建ytm静态库并安装，跳过audiotube可执行文件、QML模块、qtmpris、example

## 依赖版本

- ECM 6.0+（已安装）
- pybind11 3.0.4（pip安装）
- Qt6 6.11.1（Core/Gui/Svg/Sql/Widgets/Concurrent/DBus 可用；Qml/Quick/Multimedia/QuickControls2 不可用）
- KF6（CoreAddons/I18n/Crash/WindowSystem/Config/IconThemes 可用；Kirigami/KirigamiAddons 不可用）

## 构建产物说明

本次为OHOS minimal build，仅构建了以下组件：
- **libytm.a**: ytmusic C++静态库，封装pybind11::embed，提供ytmusicapi Python绑定接口
- **ytmusic.h**: ytm库的头文件，定义了YTMusic类及搜索/专辑/艺术家等数据结构

audiotube可执行文件（QML/Kirigami GUI音乐播放器）因缺少Qt6Qml/KF6Kirigami等关键依赖未能构建。

## 验证结果

```bash
# cmake配置成功
-- Found pybind11: /storage/Users/currentUser/.opendesk/interpreters/pip-global/pybind11/include (found version "3.0.4")
-- OHOS minimal build: skipping QML/Kirigami GUI components
-- Configuring done (12.7s)

# 编译成功
[100%] Built target ytm

# 安装成功
-- Installing: libytm.a
-- Installing: include/audiotube/ytmusic.h

# ctest: 无测试（minimal build模式）
No tests were found
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libytm.a | 816KB | ytmusic C++静态库 |
| ytmusic.h | 10KB | ytm库头文件 |
| 0001-CMakeLists.txt.patch | - | OHOS_MINIMAL_BUILD选项补丁 |
| 0002-src-CMakeLists.txt.patch | - | src目录OHOS适配补丁 |

## 注意事项

1. audiotube是KDE QML/Kirigami音乐播放器，核心功能依赖QML GUI框架，当前OHOS环境缺少Qt6Qml/Quick/Multimedia/KF6Kirigami等关键组件
2. 当上述Qt/KF QML组件可用后，可关闭OHOS_MINIMAL_BUILD选项构建完整应用
3. ytm静态库是pybind11 Python嵌入库，运行时需要Python环境和ytmusicapi/yt-dlp Python包
4. Ytdlp和YTMusicAPI是RUNTIME依赖，仅需要Python环境中有这些包即可（不影响编译）

## Conan适配修复 (2026-08-27)

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py pip install在build()中执行 | generate()先于build()执行，pybind11_DIR未设置 | 将pip3 install移至generate()，安装后立即查找cmake dir |
| 2 | test_package链接失败 | ytm PUBLIC链接pybind11::embed，消费者需libpython | 改为PRIVATE链接，ytmusic.h不依赖pybind11头文件 |
| 3 | patch 0002无法应用 | 原始src/CMakeLists.txt中DEFAULT_VALUE_GETTERS行有尾随空格 | 重新生成patch，保留尾随空格 |
| 4 | pybind11版本不固定 | pip3 install pybind11安装最新版 | 固定为pybind11==3.0.4 |
| 5 | CI #49384 find_package(pybind11) 失败 | `pip3` 与 `python3` 从 PATH 解析可能对应不同解释器，pip 装到 A 解释器的 site-packages 而 import 探测用 B 解释器，pybind11_DIR 未设置 | `_ensure_pybind11` 统一用 sys.executable 执行 pip install 和 import 探测；失败时显式 raise ConanInvalidConfiguration |
---

**编译结束**: 2026-08-27 01:12
**最终状态**: built
