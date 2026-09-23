cmake_minimum_required(VERSION 3.15)
project(test_libmaa C)

# Find the package via Conan-generated CMakeDeps
find_package(libmaa REQUIRED)

add_executable(test_libmaa test.c)
target_link_libraries(test_libmaa libmaa::libmaa)

# 鸿蒙专项测试：覆盖 timer(getrusage) 与 bit(SIZEOF_LONG=8) 两个 OHOS 平台适配点
add_executable(test_libmaa_ohos ohos_special_test.c)
target_link_libraries(test_libmaa_ohos libmaa::libmaa)
target_link_libraries(test_libmaa_ohos m)

enable_testing()
add_test(NAME test_libmaa COMMAND test_libmaa)
add_test(NAME test_libmaa_ohos COMMAND test_libmaa_ohos)
