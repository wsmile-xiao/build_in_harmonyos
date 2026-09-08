cmake_minimum_required(VERSION 3.16)
project(test_canvenient C)

find_package(CANvenient REQUIRED)

add_executable(test_canvenient test.c)
target_link_libraries(test_canvenient PRIVATE CANvenient::CANvenient)

enable_testing()
add_test(NAME canvenient_test COMMAND test_canvenient)
