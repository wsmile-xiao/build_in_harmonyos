cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(zziplib CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE zziplib::libzzip)

# CTest 侧：enable_testing() 才会生成 CTestTestfile.cmake；每个 build 树一个
# ctest-tmp 目录（configure 期创建），与 conan run 的 tmp-run 互不干扰，
# 重复/并发运行各自覆盖，不依赖任何机器路径。
enable_testing()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/ctest-tmp")
add_test(NAME test_package COMMAND test_package "${CMAKE_CURRENT_BINARY_DIR}/ctest-tmp")
