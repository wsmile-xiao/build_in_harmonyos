cmake_minimum_required(VERSION 3.15)
project(test_libx11 C)

# OHOS user toolchain (ohos.toolchain.cmake) sets
# CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY, which prevents find_package() from
# searching CMAKE_PREFIX_PATH (where conan 2's CMakeDeps generator drops the
# libx11-config.cmake we just generated). Override to BOTH so the conan
# generators directory is searched alongside the OHOS SDK native tree.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(libx11 REQUIRED)

add_executable(test_libx11 test.c)
target_link_libraries(test_libx11 PRIVATE libx11::libx11)

enable_testing()
add_test(NAME test_libx11 COMMAND test_libx11)
