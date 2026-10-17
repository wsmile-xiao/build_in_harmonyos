cmake_minimum_required(VERSION 3.15)
project(test_racon CXX)

find_package(racon REQUIRED)

add_executable(test_sequence test_sequence.cpp)
target_link_libraries(test_sequence racon::racon)

add_executable(test_polisher_types test_polisher_types.cpp)
target_link_libraries(test_polisher_types racon::racon)

enable_testing()
add_test(NAME test_sequence COMMAND test_sequence)
add_test(NAME test_polisher_types COMMAND test_polisher_types)
