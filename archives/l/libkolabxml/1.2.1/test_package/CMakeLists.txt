cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Libkolabxml REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Libkolabxml::Libkolabxml)

# Register the consumer test with CTest so `ctest -N` (MANIFEST
# upstream_check_command) discovers it and CI L1 can account for it.
enable_testing()
add_test(NAME test_package COMMAND test_package)
