cmake_minimum_required(VERSION 3.10)
project(test_package C)

include(${CMAKE_BINARY_DIR}/generators/conan_toolchain.cmake)

find_package(Orcania REQUIRED CONFIG)

add_executable(test_orcania test_orcania.c)
target_link_libraries(test_orcania PRIVATE Orcania::Orcania-static)
