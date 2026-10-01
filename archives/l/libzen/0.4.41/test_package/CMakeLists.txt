cmake_minimum_required(VERSION 3.15)
project(libzen_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ZenLib CONFIG REQUIRED)
add_executable(libzen_test test.cpp)
# The library is built with ENABLE_UNICODE=ON (UNICODE/_UNICODE are PUBLIC
# compile definitions). Define them here as well so the test's Ztring/Char
# type (tstring) matches the library build exactly (ODR-safe).
target_compile_definitions(libzen_test PRIVATE UNICODE _UNICODE)
target_link_libraries(libzen_test PRIVATE zen)
