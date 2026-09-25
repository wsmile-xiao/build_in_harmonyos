cmake_minimum_required(VERSION 3.15)
project(test_libstxxl CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(stxxl REQUIRED)

add_executable(test_stxxl test_stxxl.cpp)
target_link_libraries(test_stxxl stxxl::stxxl)

enable_testing()
add_test(NAME test_stxxl COMMAND test_stxxl)
