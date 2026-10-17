cmake_minimum_required(VERSION 3.15)
project(test_gtk2 C)

set(CMAKE_C_STANDARD 99)

# 显式 CONFIG 模式:使用 Conan CMakeDeps 生成的 GTK2-config.cmake,
# 不依赖 CMake 内置 FindGTK2 模块(3.14 弃用/4.0 移除)
find_package(GTK2 CONFIG REQUIRED)

add_executable(test_gtk2 test.c)
target_link_libraries(test_gtk2 PRIVATE GTK2::GTK2)
