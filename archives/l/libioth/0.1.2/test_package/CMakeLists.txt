cmake_minimum_required(VERSION 3.15)

project(test_libioth C)

find_package(ioth CONFIG REQUIRED)

add_executable(test_libioth test.c)

target_link_libraries(test_libioth PRIVATE ioth::ioth)

enable_testing()
add_test(NAME test_libioth COMMAND test_libioth)
