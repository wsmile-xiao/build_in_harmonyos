cmake_minimum_required(VERSION 3.15)
project(test_eventlog C)

# Find the package via Conan-generated CMakeDeps
find_package(eventlog REQUIRED)

add_executable(test_eventlog test.c)
target_link_libraries(test_eventlog eventlog::eventlog)

enable_testing()
add_test(NAME test_eventlog COMMAND test_eventlog)
