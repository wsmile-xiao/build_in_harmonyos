cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(file REQUIRED)

# System pre-compiled zlib is in $DEFAULT_PREFIX/lib,
# which is not in ld.lld's default search path on OHOS.
if(DEFINED ENV{DEFAULT_PREFIX})
    link_directories("$ENV{DEFAULT_PREFIX}/lib")
endif()

add_executable(test_package test.c)
target_link_libraries(test_package file::file)

# libmagic.a static link requires zlib; zstd and lzma are disabled in
# configure (--disable-zstdlib --disable-xzlib) and not available on OHOS
target_link_libraries(test_package z)

enable_testing()
add_test(NAME test_package COMMAND test_package)
