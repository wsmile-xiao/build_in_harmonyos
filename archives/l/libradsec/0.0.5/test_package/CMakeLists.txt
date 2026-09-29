cmake_minimum_required(VERSION 3.15)
project(test_libradsec C)

# Find the package via Conan-generated CMakeDeps
find_package(libradsec REQUIRED)

add_executable(test_libradsec test.c)
target_link_libraries(test_libradsec libradsec::libradsec)

enable_testing()
add_test(NAME test_libradsec COMMAND test_libradsec)
