cmake_minimum_required(VERSION 3.15)
project(test_kdecoration CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KDecoration3 REQUIRED)

add_executable(test_kdecoration test.cpp)
target_link_libraries(test_kdecoration KDecoration3::KDecoration)

enable_testing()
add_test(NAME test_kdecoration COMMAND test_kdecoration)
