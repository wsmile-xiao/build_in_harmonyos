cmake_minimum_required(VERSION 3.15)
project(test_libsigc2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libsigc-2 REQUIRED)

add_executable(test_libsigc2 test_package.cpp)
target_link_libraries(test_libsigc2 PRIVATE libsigc-2::libsigc-2)
