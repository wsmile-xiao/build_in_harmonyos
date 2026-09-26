cmake_minimum_required(VERSION 3.15)
project(test_rinutils C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_EXTENSIONS ON)

# Find the package via Conan-generated CMakeDeps
find_package(Rinutils REQUIRED)

add_executable(test_rinutils test.c)
target_link_libraries(test_rinutils PRIVATE Rinutils::Rinutils)

enable_testing()
add_test(NAME test_rinutils COMMAND test_rinutils)
