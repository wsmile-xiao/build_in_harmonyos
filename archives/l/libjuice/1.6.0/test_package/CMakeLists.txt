cmake_minimum_required(VERSION 3.15)
project(test_libjuice C)

# Find the package via Conan-generated CMakeDeps
find_package(libjuice REQUIRED)

add_executable(test_libjuice test.c)
target_link_libraries(test_libjuice libjuice::libjuice)

# HarmonyOS 专项测试（鸿蒙平台生命周期验证）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libjuice::libjuice)

enable_testing()
add_test(NAME test_libjuice COMMAND test_libjuice)
add_test(NAME test_ohos COMMAND test_ohos)