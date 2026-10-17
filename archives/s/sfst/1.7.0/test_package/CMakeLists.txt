cmake_minimum_required(VERSION 3.15)
project(test_sfst CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(sfst REQUIRED)

add_executable(test_sfst test_sfst.cpp)
target_link_libraries(test_sfst sfst::sfst)

enable_testing()
add_test(NAME test_sfst COMMAND test_sfst)
