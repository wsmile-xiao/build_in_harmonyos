cmake_minimum_required(VERSION 3.15)
project(test_tiny-utf8 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tinyutf8 REQUIRED)

# 消费者基础测试 (R34: 真实调用被测包 API)
add_executable(test_tiny-utf8 test.cpp)
target_link_libraries(test_tiny-utf8 tinyutf8::tinyutf8)

# HarmonyOS 专项测试 (CJK/emoji/码点边界, OHOS aarch64 工具链下运行)
add_executable(test_tiny-utf8-ohos test_ohos.cpp)
target_link_libraries(test_tiny-utf8-ohos tinyutf8::tinyutf8)

enable_testing()
add_test(NAME test_tiny-utf8 COMMAND test_tiny-utf8)
add_test(NAME test_tiny-utf8-ohos COMMAND test_tiny-utf8-ohos)