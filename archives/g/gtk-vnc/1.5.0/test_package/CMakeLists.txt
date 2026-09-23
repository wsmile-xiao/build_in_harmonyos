cmake_minimum_required(VERSION 3.15)
project(test_gtk-vnc C)

# 用 PkgConfig 方式消费（与 gtk 配方 test_package 一致）：
# gtk-vnc-2.0.pc 自带 Requires: gtk+-3.0 / gvnc-1.0，可拉通全部传递依赖
# include 路径（pango->harfbuzz 等），避免 CMakeDeps 下头文件传递问题。
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK_VNC REQUIRED IMPORTED_TARGET gtk-vnc-2.0)

add_executable(test_gtk-vnc test.c)
target_link_libraries(test_gtk-vnc PkgConfig::GTK_VNC)

enable_testing()
add_test(NAME test_gtk-vnc COMMAND test_gtk-vnc)
