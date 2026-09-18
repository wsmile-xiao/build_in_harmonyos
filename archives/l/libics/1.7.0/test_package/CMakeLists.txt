cmake_minimum_required(VERSION 3.15)
project(test_libics C)

find_package(libics REQUIRED)

add_executable(test_libics test.c)
target_link_libraries(test_libics libics::libics)

enable_testing()
add_test(NAME test_libics COMMAND test_libics)
