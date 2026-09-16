cmake_minimum_required(VERSION 3.15)
project(unittest_cpp_test CXX)

# conan 包名为 unittest-cpp（CMakeDeps 按其生成配置）；
# 配方注册了 UnitTest++ 别名 target，下游继续用上游习惯写法。
find_package(unittest-cpp REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE UnitTest++)
