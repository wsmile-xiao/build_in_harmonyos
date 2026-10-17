cmake_minimum_required(VERSION 3.15)
project(test_glob LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(glob REQUIRED)

add_executable(test_glob test.cpp)
target_link_libraries(test_glob PRIVATE glob::glob)

enable_testing()
add_test(NAME test_glob COMMAND test_glob)
