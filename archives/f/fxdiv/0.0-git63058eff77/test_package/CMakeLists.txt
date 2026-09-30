cmake_minimum_required(VERSION 3.15)
project(test_fxdiv C)

# Find the package via Conan-generated CMakeDeps
find_package(fxdiv REQUIRED)

# 消费者测试 — 通过公开头文件 fxdiv.h 调用公开 API（编译+链接+运行）
add_executable(test_fxdiv test.c)
target_link_libraries(test_fxdiv fxdiv::fxdiv)
target_compile_features(test_fxdiv PRIVATE c_std_99)

# HarmonyOS 专项测试（#ifdef __OHOS__ 实质逻辑, R6）
add_executable(test_ohos_special ohos_special_test.c)
target_link_libraries(test_ohos_special fxdiv::fxdiv)
target_compile_features(test_ohos_special PRIVATE c_std_99)

enable_testing()
add_test(NAME test_fxdiv COMMAND test_fxdiv)
add_test(NAME test_ohos_special COMMAND test_ohos_special)