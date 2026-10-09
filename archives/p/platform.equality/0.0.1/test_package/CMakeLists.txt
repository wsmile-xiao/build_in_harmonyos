cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(platform.equality REQUIRED)

add_executable(test_platform_equality test.cpp)
target_link_libraries(test_platform_equality PRIVATE platform.equality::platform.equality)
set_property(TARGET test_platform_equality PROPERTY CXX_STANDARD 20)
set_property(TARGET test_platform_equality PROPERTY CXX_STANDARD_REQUIRED ON)
# 与主配方 CMakeLists.txt 保持一致的语言模式（CXX_EXTENSIONS OFF），
# 使两层验证处于同一模式；否则消费者层会退回 gnu++20。
set_property(TARGET test_platform_equality PROPERTY CXX_EXTENSIONS OFF)
