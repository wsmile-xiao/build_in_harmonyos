cmake_minimum_required(VERSION 3.15)
project(test_smpeg2 CXX)

find_package(smpeg2 REQUIRED CONFIG)

add_executable(test_smpeg2 test_smpeg2.cpp)
target_link_libraries(test_smpeg2 PRIVATE smpeg2::smpeg2)

enable_testing()
add_test(NAME test_smpeg2 COMMAND test_smpeg2)
