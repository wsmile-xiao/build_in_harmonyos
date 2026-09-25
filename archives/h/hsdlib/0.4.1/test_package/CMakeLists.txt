cmake_minimum_required(VERSION 3.15)
project(test_hsdlib C)

# Find the package via Conan-generated CMakeDeps
find_package(hsdlib REQUIRED)

add_executable(test_hsdlib test.c)
target_link_libraries(test_hsdlib hsdlib::hsdlib)

# HarmonyOS 专项测试（运行时 SIMD 后端调度验证）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos hsdlib::hsdlib)

enable_testing()
add_test(NAME test_hsdlib COMMAND test_hsdlib)
add_test(NAME test_ohos COMMAND test_ohos)
