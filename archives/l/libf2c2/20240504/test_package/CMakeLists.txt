cmake_minimum_required(VERSION 3.15)
project(test_libf2c2 C)

find_package(libf2c2 REQUIRED)

# An ordinary C program that links the run time and calls it through f2c.h.
add_executable(test_main test_main.c)
target_link_libraries(test_main libf2c2::libf2c2)

# An f2c-translated program: it defines MAIN__ instead of main(), so the
# entry point and the run-time start-up/shutdown come from the library.
add_executable(test_startup test_startup.c)
target_link_libraries(test_startup libf2c2::libf2c2)
