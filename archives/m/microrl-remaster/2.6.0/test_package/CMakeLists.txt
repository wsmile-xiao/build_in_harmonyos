cmake_minimum_required(VERSION 3.15)
project(test_microrl_remaster C)

# Find the package via Conan-generated CMakeDeps
find_package(microrl-remaster REQUIRED)

add_executable(test_microrl_remaster test.c)
target_link_libraries(test_microrl_remaster microrl-remaster::microrl-remaster)

# HarmonyOS 专项测试（OHOS arm64 平台识别 + 公开 API 断言）
add_executable(test_microrl_remaster_ohos test_ohos.c)
target_link_libraries(test_microrl_remaster_ohos microrl-remaster::microrl-remaster)

enable_testing()
add_test(NAME test_microrl_remaster COMMAND test_microrl_remaster)
add_test(NAME test_microrl_remaster_ohos COMMAND test_microrl_remaster_ohos)
