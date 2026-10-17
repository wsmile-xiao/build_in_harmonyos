cmake_minimum_required(VERSION 3.15)
project(test_lcrq C)

# Find the package via Conan-generated CMakeDeps
find_package(lcrq REQUIRED)

add_executable(test_lcrq test.c)
target_link_libraries(test_lcrq lcrq::lcrq)

# 鸿蒙特有测试 (rule12): OHOS musl 运行时 + aarch64 平台 + RaptorQ 回环
add_executable(test_lcrq_ohos test_ohos.c)
target_link_libraries(test_lcrq_ohos lcrq::lcrq)

enable_testing()
add_test(NAME test_lcrq COMMAND test_lcrq)
add_test(NAME test_lcrq_ohos COMMAND test_lcrq_ohos)
