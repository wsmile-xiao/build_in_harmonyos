cmake_minimum_required(VERSION 3.15)
project(test_bytes C)

# Find the package via Conan-generated CMakeDeps
find_package(bytes REQUIRED)

add_executable(test_bytes test.c)
target_link_libraries(test_bytes bytes::bytes)

# HarmonyOS 专项测试（新增用例，区别于上游 test.c 与消费者 test.c）
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test bytes::bytes)

enable_testing()
add_test(NAME test_bytes COMMAND test_bytes)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)
