cmake_minimum_required(VERSION 3.15)
project(test_sgc CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(sigc++ REQUIRED)

add_executable(test_package test_package.cc)
target_link_libraries(test_package sigc++::sigc++)

enable_testing()
add_test(NAME test_sgc COMMAND test_package)
