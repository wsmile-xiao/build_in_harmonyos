cmake_minimum_required(VERSION 3.15)
project(test_orc C)

find_package(orc REQUIRED)

add_executable(test_orc test_orc.c)
target_link_libraries(test_orc PRIVATE orc::orc)

enable_testing()
add_test(NAME test_orc COMMAND test_orc)
