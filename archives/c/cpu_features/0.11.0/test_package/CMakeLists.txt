cmake_minimum_required(VERSION 3.15)
project(test_cpu_features C)

# Find the package via Conan-generated CMakeDeps
find_package(cpu_features REQUIRED)

add_executable(test_cpu_features test.c)
target_link_libraries(test_cpu_features cpu_features::cpu_features)

enable_testing()
add_test(NAME test_cpu_features COMMAND test_cpu_features)

# OHOS 专项测试: 校验库在 OHOS 运行时读取真实硬件信息
add_executable(test_cpu_features_ohos test_ohos.c)
target_link_libraries(test_cpu_features_ohos cpu_features::cpu_features)
add_test(NAME test_cpu_features_ohos COMMAND test_cpu_features_ohos)
