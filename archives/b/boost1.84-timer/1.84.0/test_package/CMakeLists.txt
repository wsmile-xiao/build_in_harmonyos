cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_timer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-timer REQUIRED CONFIG COMPONENTS timer)

add_executable(test_boost1_84_timer test_boost1_84_timer.cpp)
target_link_libraries(test_boost1_84_timer PRIVATE boost1.84-timer::timer)

enable_testing()
add_test(NAME boost1_84_timer_test COMMAND test_boost1_84_timer)
