cmake_minimum_required(VERSION 3.15)
project(test_npth C)

# Find the package via Conan-generated CMakeDeps
find_package(npth REQUIRED)

add_executable(test_npth test.c)
target_link_libraries(test_npth npth::npth)

# 鸿蒙特有测试：OHOS/musl 平台点（平台宏、pthread_tryjoin_np 缺失、线程调度回归）
add_executable(test_npth_ohos test_npth_ohos.c)
target_link_libraries(test_npth_ohos npth::npth)

enable_testing()
add_test(NAME test_npth COMMAND test_npth)
add_test(NAME test_npth_ohos COMMAND test_npth_ohos)
