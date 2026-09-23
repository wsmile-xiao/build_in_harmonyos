cmake_minimum_required(VERSION 3.15)
project(test_libpar2 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libpar2 REQUIRED)

add_executable(test_libpar2 test.cpp)
target_link_libraries(test_libpar2 libpar2::libpar2)
# libpar2 公开头文件 include <sigc++/sigc++.h>；预编译 libsigc 二进制的
# CMakeDeps 未传递 include 目录（实测），由 test_package 生成器显式注入
if(DEFINED LIBSIGC_INCLUDE_DIRS)
    target_include_directories(test_libpar2 PRIVATE ${LIBSIGC_INCLUDE_DIRS})
endif()

enable_testing()
add_test(NAME test_libpar2 COMMAND test_libpar2)