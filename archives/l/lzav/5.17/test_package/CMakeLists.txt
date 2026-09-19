cmake_minimum_required(VERSION 3.15)
project(lzav_test_package C)

find_package(lzav REQUIRED)

add_executable(lzav_consumer_test test.c)
target_link_libraries(lzav_consumer_test PRIVATE lzav::lzav)

# HarmonyOS-specific platform test (compiled for/verified at runtime on OHOS)
add_executable(lzav_ohos_test test_ohos.c)
target_link_libraries(lzav_ohos_test PRIVATE lzav::lzav)
