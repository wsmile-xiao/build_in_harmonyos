cmake_minimum_required(VERSION 3.15)
project(test_libgoa C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 由 Conan CMakeDeps 生成的 libgoa-config.cmake 提供 libgoa::libgoa
find_package(libgoa REQUIRED)

add_executable(test_goa_consumer test_goa_consumer.c)
target_compile_options(test_goa_consumer PRIVATE -Wall -Wextra)
target_link_libraries(test_goa_consumer PRIVATE libgoa::libgoa)

enable_testing()
add_test(NAME test_goa_consumer COMMAND test_goa_consumer)
