cmake_minimum_required(VERSION 3.15)
project(test_nsync C)

find_package(nsync REQUIRED)

find_package(Threads REQUIRED)

add_executable(test_nsync test.c)
target_link_libraries(test_nsync nsync::nsync Threads::Threads)

enable_testing()
add_test(NAME test_nsync COMMAND test_nsync)
