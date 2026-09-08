# qt5 5.15.19 适配笔记

## 编译环境
- 构建系统: configure + qmake
- 编译日期: 2026-08-24
- 编译器: clang/clang++ 15.0.4 (OHOS SDK)
- 状态: built

## 编译步骤
1. 下载 qtbase-everywhere-opensource-src-5.15.19.tar.xz
2. 解压并创建工作目录
3. 应用5个补丁（abstract socket, pthread_cancel, socklen_t, qmake host OS）
4. 配置: ./configure -prefix /usr/local -opensource -confirm-license -no-dbus -no-accessibility -opengl es2 -no-xcb -no-eglfs -no-linuxfb -no-feature-sql -no-feature-systemsemaphore -no-feature-sharedmemory -nomake tests -nomake examples -no-iconv -no-glib -no-icu -no-vulkan -no-openssl -no-libproxy -no-system-proxies -system-zlib -platform linux-clang
5. 编译: make -j4 QMAKE_STRIP=""
6. 安装: make install QMAKE_STRIP=""

## 上游测试状态
- 18个测试类别（corelib, network, gui, widgets, concurrent, xml等）
- 测试套件已构建但因运行时符号解析问题无法直接运行
- 102个测试点的消费者测试集（test_qt5_all.cpp）全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel/pthread_setcancelstate 未定义 | OHOS musl 不提供 pthread_cancel | 添加 __OHOS__ 条件编译守卫 |
| 2 | socklen_t 类型不匹配 | OHOS musl 的 socklen_t 是 unsigned int，但 Qt 定义为 int | 添加 __OHOS__ 判断使用 socklen_t |
| 3 | qmake "Operating system not supported" | qmake 的 OS 检测不支持 OHOS | 修改 qt_functions.prf，添加 OHOS 回退到 LD_LIBRARY_PATH |
| 4 | dbus 模块无法编译 | qdbusxml2cpp 工具不支持 OHOS | 配置时用 -no-dbus 禁用 dbus 模块 |
| 5 | 无 QPA 平台插件 | OHOS 无 X11/Wayland | 配置时使用 -no-xcb -no-eglfs -no-linuxfb，仅核心库可用 |
| 6 | 抽象套接字绑定失败 | OHOS 不允许文件式 Unix 域套接字 bind() | 使用抽象套接字命名空间（sun_path[0]='\0'） |

## 编译产物
- libQt5Core.so.5.15.19 (7.3MB)
- libQt5Gui.so.5.15.19 (7.7MB)
- libQt5Network.so.5.15.19 (1.5MB)
- libQt5Widgets.so.5.15.19 (7.2MB)
- libQt5Test.so.5.15.19 (416KB)
- libQt5Xml.so.5.15.19
- libQt5Concurrent.so.5.15.19
- libQt5OpenGL.so.5.15.19
- libQt5PrintSupport.so.5.15.19
- 总计 36 个共享库, 多个插件, qmake/moc/uic/rcc 等工具