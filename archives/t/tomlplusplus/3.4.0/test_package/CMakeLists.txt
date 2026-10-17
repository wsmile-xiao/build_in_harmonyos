cmake_minimum_required(VERSION 3.15)
project(test_tomlplusplus CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(tomlplusplus REQUIRED)

add_executable(test_tomlplusplus test.cpp)
target_link_libraries(test_tomlplusplus tomlplusplus::tomlplusplus)

enable_testing()
add_test(NAME test_tomlplusplus COMMAND test_tomlplusplus)
