cmake_minimum_required(VERSION 3.15)
project(test_vvenc CXX)

# vvenc packages an upstream CMake config file; the exported target is vvenc::vvenc.
find_package(vvenc REQUIRED)

add_executable(test_vvenc test_vvenc.cpp)
target_link_libraries(test_vvenc vvenc::vvenc)

enable_testing()
add_test(NAME test_vvenc COMMAND test_vvenc)
