cmake_minimum_required(VERSION 3.15)
project(test_libopenv2g C)

# Allow Conan's generated package config to be found alongside the OHOS SDK
# root used by the PC toolchain.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(libopenv2g REQUIRED CONFIG)

add_executable(test_libopenv2g test.c)
target_link_libraries(test_libopenv2g PRIVATE libopenv2g::libopenv2g)

enable_testing()
add_test(NAME test_libopenv2g COMMAND test_libopenv2g)
