cmake_minimum_required(VERSION 3.15)
project(test_libxcb C)

# OHOS user toolchain (ohos.toolchain.cmake) sets
# CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY, which prevents find_package() from
# searching CMAKE_PREFIX_PATH (where conan 2's CMakeDeps generator drops the
# libxcb-config.cmake we just generated). Override to BOTH so the conan
# generators directory is searched alongside the OHOS SDK native tree.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(libxcb REQUIRED)

add_executable(test_libxcb test.c)
target_link_libraries(test_libxcb PRIVATE libxcb::libxcb)

enable_testing()
add_test(NAME test_libxcb COMMAND test_libxcb)