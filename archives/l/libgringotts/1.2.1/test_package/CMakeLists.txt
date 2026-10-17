cmake_minimum_required(VERSION 3.15)
project(test_libgringotts C)

# Find the package via Conan-generated CMakeDeps
find_package(libgringotts REQUIRED)

add_executable(test_libgringotts test.c)
target_link_libraries(test_libgringotts libgringotts::libgringotts)

enable_testing()
add_test(NAME test_libgringotts COMMAND test_libgringotts)
