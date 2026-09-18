cmake_minimum_required(VERSION 3.15)
project(test_libeio C)

# Find the package via Conan-generated CMakeDeps
find_package(libeio REQUIRED)

add_executable(test_libeio test.c)
target_link_libraries(test_libeio libeio::libeio)

enable_testing()
add_test(NAME test_libeio COMMAND test_libeio)
