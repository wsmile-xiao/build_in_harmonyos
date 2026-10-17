cmake_minimum_required(VERSION 3.5)
project(test_gli LANGUAGES CXX)

find_package(gli REQUIRED)

add_executable(test_gli test_package.cpp)
target_link_libraries(test_gli PRIVATE gli::gli)
