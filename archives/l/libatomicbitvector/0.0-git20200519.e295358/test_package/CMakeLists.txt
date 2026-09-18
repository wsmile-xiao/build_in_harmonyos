cmake_minimum_required(VERSION 3.15)
project(test_atomicbitvector CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(atomicbitvector REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_atomicbitvector test_atomicbitvector.cpp)
target_link_libraries(test_atomicbitvector PRIVATE atomicbitvector::atomicbitvector Threads::Threads)

enable_testing()
add_test(NAME test_atomicbitvector COMMAND test_atomicbitvector)
