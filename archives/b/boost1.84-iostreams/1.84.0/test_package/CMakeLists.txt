cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_iostreams CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-iostreams REQUIRED CONFIG COMPONENTS iostreams)

add_executable(test_boost1_84_iostreams test_boost_iostreams.cpp)
target_link_libraries(test_boost1_84_iostreams PRIVATE boost1.84-iostreams::iostreams)

enable_testing()
add_test(NAME boost1_84_iostreams_test COMMAND test_boost1_84_iostreams)
