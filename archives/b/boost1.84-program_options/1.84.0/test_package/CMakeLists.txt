cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_program_options CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-program_options REQUIRED CONFIG COMPONENTS program_options)

add_executable(test_boost1_84_program_options test_boost1_84_program_options.cpp)
target_link_libraries(test_boost1_84_program_options PRIVATE boost1.84-program_options::program_options)

enable_testing()
add_test(NAME boost1_84_program_options_test COMMAND test_boost1_84_program_options)
