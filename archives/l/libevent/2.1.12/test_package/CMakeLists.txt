cmake_minimum_required(VERSION 3.15)
project(test_libevent C)

# Find the package via Conan-generated CMakeDeps
find_package(libevent REQUIRED)

add_executable(test_libevent test.c)
target_link_libraries(test_libevent libevent::libevent)

enable_testing()
add_test(NAME test_libevent COMMAND test_libevent)
