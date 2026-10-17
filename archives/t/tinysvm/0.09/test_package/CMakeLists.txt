cmake_minimum_required(VERSION 3.15)
project(tinysvm_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(tinysvm CONFIG REQUIRED)

add_executable(tinysvm_api_test test_tinysvm.cpp)
target_link_libraries(tinysvm_api_test PRIVATE tinysvm::tinysvm)
