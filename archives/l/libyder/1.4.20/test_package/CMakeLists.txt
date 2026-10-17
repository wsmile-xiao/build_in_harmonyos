cmake_minimum_required(VERSION 3.10)
project(test_package C)

include(${CMAKE_BINARY_DIR}/generators/conan_toolchain.cmake)

find_package(Yder REQUIRED CONFIG)

add_executable(test_yder test_yder.c)
target_link_libraries(test_yder PRIVATE Yder::Yder-static)
