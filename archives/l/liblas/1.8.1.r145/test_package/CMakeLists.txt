cmake_minimum_required(VERSION 3.15)
project(test_liblas CXX)

find_package(libLAS REQUIRED)

add_executable(test_liblas test_liblas.cpp)
target_link_libraries(test_liblas libLAS::las)

enable_testing()
add_test(NAME test_liblas COMMAND $<TARGET_FILE:test_liblas>)
