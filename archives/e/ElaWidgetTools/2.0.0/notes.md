# ElaWidgetTools 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-24
- 编译器: clang 15.0.4 / clang++ 15.0.4 (HarmonyOS SDK)
- C++ 标准库: libc++ (非 libstdc++)
- 系统: HarmonyOS aarch64, HongMeng Kernel 1.12.0
- 状态: 成功 (published)

## 依赖版本
- Qt5 qtbase 5.15.2（从源码编译，安装路径: $HOME/usr/local/Qt5）

## 编译步骤

### 1. 编译安装 Qt5 qtbase 5.15.2（前置依赖）

HarmonyOS 无预编译 Qt5 包，需从源码编译。

```bash
# 下载源码
curl --insecure -o $HOME/tmp/qtbase-5.15.2.tar.gz \
  https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qtbase-everywhere-src-5.15.2.tar.xz

# 解压
cd $HOME/tmp && tar xf qtbase-5.15.2.tar.gz

# 生成头文件
cd qtbase-5.15.2
perl bin/syncqt.pl

# 配置
./configure -platform linux-clang-libc++ -prefix $HOME/usr/local/Qt5 \
  -opensource -confirm-license -no-opengl -no-dbus -no-sql-sqlite \
  -no-icu -no-accessibility -qt-freetype -qt-harfbuzz -qt-pcre -qt-zlib \
  -nomake tests -nomake examples

# 编译和安装
make -j2
make install

# 复制非 stripped 的工具和库（HarmonyOS 上 stripped 二进制无法执行）
cp bin/{moc,rcc,uic,qmake} $HOME/usr/local/Qt5/bin/
cp lib/libQt5*.so.5.15.2 $HOME/usr/local/Qt5/lib/
```

### 2. 编译 ElaWidgetTools 2.0.0

```bash
# 修改 CMakeLists.txt
# - QT_SDK_DIR 改为 $ENV{HOME}/usr/local/Qt5
# - CMAKE_INSTALL_PREFIX 移除 FORCE
# - 注释掉 add_subdirectory(ElaWidgetToolsExample)

# 配置
mkdir -p build && cd build
cmake .. \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local/Qt5 \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
  -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++" \
  -DCMAKE_SHARED_LINKER_FLAGS="-stdlib=libc++" \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DELAWIDGETTOOLS_BUILD_STATIC_LIB=ON

# 编译
make -j2

# 安装到测试目录 (DESTDIR 模式)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt5 编译错误: musl libc 不支持 pthread_cancel | HarmonyOS 使用 musl libc，不支持 pthread_cancel/pthread_setcancelstate/pthread_testcancel | 在 qthread_unix.cpp 中用 `#if !defined(__OHOS__)` 保护 4 处 pthread_cancel 相关代码 |
| 2 | Qt5 编译错误: socklen_t 类型不匹配 | HarmonyOS 上 socklen_t 为 unsigned int，Qt 原始代码在非 glibc 平台定义为 int | 修改 mkspecs/linux-clang/qplatformdefs.h，将 QT_SOCKLEN_T 从 int 改为 socklen_t |
| 3 | Qt5 GUI 模块错误: Operating system not supported | qt_functions.prf 中 QMAKE_HOST.os 检测不支持 HarmonyOS | 在 qt_functions.prf 的 contains() 检测列表中添加 HarmonyOS |
| 4 | cmake 生成失败: moc 执行 "Operation not permitted" | HarmonyOS 上 stripped 的 ELF 二进制无法执行 | 从 Qt5 构建目录复制非 stripped 的工具（moc/rcc/uic 等）到安装目录 |
| 5 | uic 运行时找不到 libQt5Core.so.5 | 安装的 libQt5Core.so.5.15.2 是 stripped 版本，无法被动态加载 | 从 Qt5 构建目录复制非 stripped 的库文件 |
| 6 | cmake 安装路径不正确 | CMakeLists.txt 中 CMAKE_INSTALL_PREFIX 使用 FORCE 硬编码为源码目录 | 移除 FORCE 关键字，改为可被命令行覆盖 |

## 源码修改
1. **CMakeLists.txt**:
   - `SET(QT_SDK_DIR D:/Qt/5.15.2/msvc2019_64` → `SET(QT_SDK_DIR $ENV{HOME}/usr/local/Qt5`
   - `SET(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/Install CACHE PATH "Installation path" FORCE)` → `set(CMAKE_INSTALL_PREFIX ${CMAKE_INSTALL_PREFIX} CACHE PATH "Installation path")`
   - `add_subdirectory(ElaWidgetToolsExample)` → `#add_subdirectory(ElaWidgetToolsExample)`

2. **Qt5 源码补丁**（详见上方问题描述）:
   - qthread_unix.cpp: 4 处 pthread_cancel 相关代码
   - qplatformdefs.h: QT_SOCKLEN_T 类型定义
   - qt_functions.prf: 添加 HarmonyOS 到 OS 检测列表

## 验证结果
- 静态库 libElaWidgetTools.a 编译成功（15.3MB，195 个目标文件）
- 70 个头文件正确安装
- CMake 配置文件（ElaWidgetToolsConfig.cmake 等）正确生成
- 无可执行文件（静态库，R7 安全弹窗验证通过）

## 交付物
- 静态库: `$DEFAULT_PREFIX/ElaWidgetTools/lib/libElaWidgetTools.a`
- 头文件: `$DEFAULT_PREFIX/ElaWidgetTools/include/*.h`（70 个文件）
- CMake 配置: `$DEFAULT_PREFIX/ElaWidgetTools/lib/cmake/`（4 个文件）
---

**编译结束**: 2026-06-24 19:11
**最终状态**: published
