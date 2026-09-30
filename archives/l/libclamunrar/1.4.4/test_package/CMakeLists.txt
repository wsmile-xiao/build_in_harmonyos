cmake_minimum_required(VERSION 3.15)
project(test_libclamunrar CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libclamunrar REQUIRED)

add_executable(test_libclamunrar test_libclamunrar.cpp)
target_link_libraries(test_libclamunrar PRIVATE libclamunrar::libclamunrar)
