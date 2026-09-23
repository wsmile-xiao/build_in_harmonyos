cmake_minimum_required(VERSION 3.15)
project(libopencad_consumer CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libopencad CONFIG REQUIRED)

add_executable(test_libopencad test_libopencad.cpp)
target_compile_options(test_libopencad PRIVATE -Wall -Wextra)
target_link_libraries(test_libopencad PRIVATE libopencad::libopencad)
