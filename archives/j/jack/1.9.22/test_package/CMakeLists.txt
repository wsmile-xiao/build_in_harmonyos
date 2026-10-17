cmake_minimum_required(VERSION 3.15)
project(test_jack CXX)

find_package(jack REQUIRED)

add_executable(test_jack test_jack.cpp)
target_link_libraries(test_jack jack::jack)

enable_testing()
add_test(NAME test_jack COMMAND test_jack)
