cmake_minimum_required(VERSION 3.15)
project(test_glbinding CXX)

# Find the package via Conan-generated CMakeDeps
find_package(glbinding REQUIRED)

add_executable(test_glbinding test.cpp)
target_link_libraries(test_glbinding glbinding::glbinding)

# HarmonyOS 专项测试：验证公开 API 与 OHOS 系统 GL 运行时集成点
add_executable(test_glbinding_ohos test_ohos.cpp)
target_link_libraries(test_glbinding_ohos glbinding::glbinding)

enable_testing()
add_test(NAME test_glbinding COMMAND test_glbinding)
add_test(NAME test_glbinding_ohos COMMAND test_glbinding_ohos)
