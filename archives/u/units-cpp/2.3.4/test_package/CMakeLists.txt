cmake_minimum_required(VERSION 3.15)
project(test_units CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(units REQUIRED)

add_executable(test_units test_units.cpp)
target_link_libraries(test_units PRIVATE units::units)

enable_testing()
add_test(NAME test_units COMMAND test_units)
