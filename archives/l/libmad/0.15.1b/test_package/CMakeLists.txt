cmake_minimum_required(VERSION 3.15)
project(test_libmad C)

# Find the package via Conan-generated CMakeDeps
find_package(libmad REQUIRED)

add_executable(test_libmad test.c)
target_link_libraries(test_libmad libmad::libmad)

# HarmonyOS (aarch64) 专项测试：真实 MPEG 帧解码验证定点运算
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libmad::libmad)

enable_testing()
add_test(NAME test_libmad COMMAND test_libmad)
add_test(NAME test_ohos COMMAND test_ohos)