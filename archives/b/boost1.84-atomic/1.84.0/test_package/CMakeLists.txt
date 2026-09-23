cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_atomic CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-atomic REQUIRED CONFIG COMPONENTS atomic)

add_executable(test_boost1_84_atomic test_boost_atomic.cpp)
target_link_libraries(test_boost1_84_atomic PRIVATE boost1.84-atomic::atomic)

enable_testing()
add_test(NAME boost1_84_atomic_test COMMAND test_boost1_84_atomic)
