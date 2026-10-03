cmake_minimum_required(VERSION 3.15)
project(test_mtxclient CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package through the CMakeDeps-generated MatrixClientConfig.cmake,
# i.e. exactly the way a downstream consumer of the Conan package would.
find_package(MatrixClient CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE MatrixClient::MatrixClient)

enable_testing()
add_test(NAME test_package COMMAND test_package)
