cmake_minimum_required(VERSION 3.15)
project(test_hsluv_consumer C)

# Find the package via Conan-generated CMakeDeps
find_package(hsluv-c REQUIRED)

add_executable(test_hsluv_consumer test_hsluv_consumer.c)
target_link_libraries(test_hsluv_consumer hsluv-c::hsluv-c)

# 鸿蒙专项测试：OHOS 目标下库的数值不变量与边界行为验证
add_executable(test_hsluv_ohos test_hsluv_ohos.c)
target_link_libraries(test_hsluv_ohos hsluv-c::hsluv-c)
target_compile_features(test_hsluv_ohos PRIVATE c_std_99)

enable_testing()
add_test(NAME test_hsluv_consumer COMMAND test_hsluv_consumer)
add_test(NAME test_hsluv_ohos COMMAND test_hsluv_ohos)
