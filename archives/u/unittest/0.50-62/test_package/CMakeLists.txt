cmake_minimum_required(VERSION 3.15)
project(unittest_test_package LANGUAGES CXX)

# Conan CMakeDeps 生成的 Config（包名 unittest → 配置 unittest-config.cmake，
# 目标 unittest::unittest）。被测库为静态库 libunittest.a，公共头在
# include/unittest/ 下，消费者以 <unittest/UnitTest.hpp> 引用。
find_package(unittest REQUIRED)

# 消费者验证（8 个用例，真实调用框架公共 API）
add_executable(test_unittest test_unittest.cpp)
target_link_libraries(test_unittest PRIVATE unittest::unittest)

enable_testing()
add_test(NAME test_unittest COMMAND test_unittest)
