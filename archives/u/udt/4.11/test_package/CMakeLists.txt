cmake_minimum_required(VERSION 3.15)
project(udt_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(udt CONFIG REQUIRED)
add_executable(test_udt test.cpp)
target_link_libraries(test_udt PRIVATE udt::udt)
# UDT uses socket/pthread on POSIX; link thread explicitly.
find_package(Threads REQUIRED)
target_link_libraries(test_udt PRIVATE Threads::Threads)
