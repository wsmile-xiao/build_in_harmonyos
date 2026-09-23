cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_nowide CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-nowide REQUIRED CONFIG COMPONENTS nowide)

add_executable(test_boost1_84_nowide test_boost_nowide.cpp)
target_link_libraries(test_boost1_84_nowide PRIVATE boost1.84-nowide::nowide)

enable_testing()
add_test(NAME boost1_84_nowide_test COMMAND test_boost1_84_nowide)
