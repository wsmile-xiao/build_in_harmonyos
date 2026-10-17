cmake_minimum_required(VERSION 3.15)
project(test_afflib C)

# Find the package via Conan-generated CMakeDeps
find_package(afflib REQUIRED)

add_executable(test_afflib test.c)
target_link_libraries(test_afflib afflib::afflib)

enable_testing()
add_test(NAME test_afflib COMMAND test_afflib)
