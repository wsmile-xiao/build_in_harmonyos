cmake_minimum_required(VERSION 3.15)
project(test_libsigcplusplus LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libsigcplusplus REQUIRED)

add_executable(test_libsigcplusplus test_package.cpp)
target_link_libraries(test_libsigcplusplus PRIVATE libsigcplusplus::libsigcplusplus)
