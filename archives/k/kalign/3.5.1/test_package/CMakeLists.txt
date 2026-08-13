cmake_minimum_required(VERSION 3.15)
project(test_kalign C)

find_package(kalign REQUIRED)

add_executable(test_kalign test.c)
target_link_libraries(test_kalign kalign::kalign)

enable_testing()
add_test(NAME test_kalign COMMAND test_kalign)
