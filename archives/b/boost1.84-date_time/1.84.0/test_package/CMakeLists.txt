cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_date_time CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-date_time REQUIRED CONFIG COMPONENTS date_time)

add_executable(test_boost1_84_date_time test_boost1_84_date_time.cpp)
target_link_libraries(test_boost1_84_date_time PRIVATE boost1.84-date_time::date_time)

enable_testing()
add_test(NAME boost1_84_date_time_test COMMAND test_boost1_84_date_time)
