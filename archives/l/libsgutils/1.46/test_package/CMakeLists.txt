cmake_minimum_required(VERSION 3.15)
project(test_libsgutils C)

# Find the package via Conan-generated CMakeDeps
find_package(libsgutils REQUIRED)

# 消费者用例：仅经公开头文件/API 使用库
add_executable(test_libsgutils test.c)
target_link_libraries(test_libsgutils libsgutils::libsgutils)

# 鸿蒙专项测试：OHOS 平台 sense 解码正确性
add_executable(test_libsgutils_ohos ohos_test.c)
target_link_libraries(test_libsgutils_ohos libsgutils::libsgutils)

enable_testing()
add_test(NAME test_libsgutils COMMAND test_libsgutils)
add_test(NAME test_libsgutils_ohos COMMAND test_libsgutils_ohos)