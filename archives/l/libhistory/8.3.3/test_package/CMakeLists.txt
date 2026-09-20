cmake_minimum_required(VERSION 3.5)
project(test_libhistory C)

find_package(libhistory REQUIRED)

add_executable(test_libhistory test_history.c)
target_link_libraries(test_libhistory PRIVATE libhistory::libhistory)

enable_testing()
add_test(NAME test_libhistory COMMAND test_libhistory)
