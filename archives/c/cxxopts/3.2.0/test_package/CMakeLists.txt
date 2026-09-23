cmake_minimum_required(VERSION 3.15)
project(test_cxxopts LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(cxxopts CONFIG REQUIRED)

add_executable(test_cxxopts test.cpp)
target_link_libraries(test_cxxopts PRIVATE cxxopts::cxxopts)

enable_testing()
add_test(NAME test_cxxopts COMMAND test_cxxopts)
