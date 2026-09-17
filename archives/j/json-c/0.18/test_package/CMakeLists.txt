cmake_minimum_required(VERSION 3.15)
project(test_json-c C)

# Find the package via Conan-generated CMakeDeps
find_package(json-c REQUIRED)

add_executable(test_json-c test.c)
target_link_libraries(test_json-c json-c::json-c)

# HarmonyOS 专项测试：验证 UTF-8 中文往返、大 int64、嵌套数组迭代等平台相关能力
add_executable(test_ohos_specific test_ohos_specific.c)
target_link_libraries(test_ohos_specific json-c::json-c)

enable_testing()
add_test(NAME test_json-c COMMAND test_json-c)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
