cmake_minimum_required(VERSION 3.15)
project(test_libhmsbeagle C)

find_package(libhmsbeagle REQUIRED)

add_executable(test_libhmsbeagle test.c)
target_link_libraries(test_libhmsbeagle PRIVATE libhmsbeagle::libhmsbeagle)

enable_testing()
add_test(NAME test_libhmsbeagle COMMAND test_libhmsbeagle)
