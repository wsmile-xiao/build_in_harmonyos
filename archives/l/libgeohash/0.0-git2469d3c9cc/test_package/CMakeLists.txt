cmake_minimum_required(VERSION 3.15)
project(test_libgeohash C)

# Find the package via Conan-generated CMakeDeps
find_package(libgeohash REQUIRED)

enable_testing()

add_executable(test_libgeohash test.c)
target_link_libraries(test_libgeohash libgeohash::libgeohash)
add_test(NAME test_libgeohash COMMAND test_libgeohash)

# HarmonyOS 专项测试（与消费者测试分别计数）
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test libgeohash::libgeohash)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)
