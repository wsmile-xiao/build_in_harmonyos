cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(gamelib CONFIG REQUIRED)

add_executable(test_gamelib test_gamelib.cpp)
target_link_libraries(test_gamelib PRIVATE gamelib::gamelib)

add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test PRIVATE gamelib::gamelib)

enable_testing()
add_test(NAME test_gamelib COMMAND test_gamelib)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
