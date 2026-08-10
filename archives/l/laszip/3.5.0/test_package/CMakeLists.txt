cmake_minimum_required(VERSION 3.15)
project(test_laszip C)

find_package(laszip REQUIRED)

add_executable(test_laszip test.c)
target_link_libraries(test_laszip laszip::laszip)

enable_testing()
add_test(NAME test_laszip COMMAND test_laszip)
