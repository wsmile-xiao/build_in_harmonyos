cmake_minimum_required(VERSION 3.15)
project(test_libdaemon C)

# Find the package via Conan-generated CMakeDeps
find_package(libdaemon REQUIRED)

add_executable(test_libdaemon test.c)
target_link_libraries(test_libdaemon libdaemon::libdaemon)

enable_testing()
add_test(NAME test_libdaemon COMMAND test_libdaemon)
