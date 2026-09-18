cmake_minimum_required(VERSION 3.15)
project(test_openmm CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(openmm REQUIRED)

add_executable(test_openmm test_openmm.cpp)
target_link_libraries(test_openmm openmm::openmm)

enable_testing()
add_test(NAME test_openmm COMMAND test_openmm)
