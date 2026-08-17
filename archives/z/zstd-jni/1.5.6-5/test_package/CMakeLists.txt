cmake_minimum_required(VERSION 3.15)
project(test_zstd_jni C)

find_package(zstd-jni REQUIRED)

add_executable(test_zstd_jni test.c)
target_link_libraries(test_zstd_jni zstd-jni::zstd-jni)

enable_testing()
add_test(NAME test_zstd_jni COMMAND test_zstd_jni)
