cmake_minimum_required(VERSION 3.15)
project(test_wyhash LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(wyhash CONFIG REQUIRED)

add_executable(test_wyhash test_wyhash.cpp)
target_link_libraries(test_wyhash PRIVATE wyhash::wyhash)

enable_testing()
add_test(NAME test_wyhash COMMAND test_wyhash)
