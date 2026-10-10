cmake_minimum_required(VERSION 3.16)
project(kwayland_roundtrip C CXX)

# qtbase/kwayland 都是 cmake_find_mode=none：CMakeDeps 不生成也不加
# CMAKE_PREFIX_PATH，消费者显式 prepend（kdecoration/libkscreen 先例）
list(PREPEND CMAKE_PREFIX_PATH "${QT6_CMAKE_DIR}")
list(PREPEND CMAKE_PREFIX_PATH "${KWAYLAND_CMAKE_DIR}")

# KWaylandConfig.cmake 只有 find_dependency(Qt6Gui)；本测试自身用
# Qt6::Core 跑事件循环
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KWayland REQUIRED)
# wayland 由 Qt6 自带的 ECM 组件式 find 模块（Findwayland.cmake，Qt6Config
# 把 .../Qt6/3rdparty/extra-cmake-modules/find-modules 加进 CMAKE_MODULE_PATH）
# 解析：test_package 只用 CMakeToolchain、没有 CMakeDeps 生成的
# wayland-config.cmake，故 find_package(Wayland) 走模块模式，模块给出
# Wayland::Client / Wayland::Server / Wayland::Cursor / Wayland::Egl
# 四个导入目标（不存在 CMakeDeps 风格的 wayland::wayland 全局目标）。
# 模块经 pkg-config 定位到 conan wayland/1.22.0 包（conanbuild 提供
# PKG_CONFIG_PATH），库路径与头文件都由目标携带
find_package(Wayland REQUIRED COMPONENTS Client Server)
find_package(Threads REQUIRED)

# 进程内迷你 Wayland 合成器（服务端线程，见 src/mini_compositor.c）
add_library(mini_compositor STATIC src/mini_compositor.c)
target_link_libraries(mini_compositor PRIVATE Wayland::Client Wayland::Server Threads::Threads)

# E2E 往返：KWaylandClient 全链路接入迷你合成器
add_executable(client_roundtrip src/client_roundtrip.cpp)
target_link_libraries(client_roundtrip PRIVATE
    Plasma::KWaylandClient
    Qt6::Core
    mini_compositor
)
