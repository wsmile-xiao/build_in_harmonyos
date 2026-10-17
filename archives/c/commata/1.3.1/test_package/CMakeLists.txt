cmake_minimum_required(VERSION 3.15)
project(test_commata CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(commata REQUIRED)

add_executable(test_commata test.cpp)
target_link_libraries(test_commata commata::commata)

enable_testing()
add_test(NAME test_commata COMMAND test_commata)
