cmake_minimum_required(VERSION 3.15)
project(test_bstrlib C)

# Find the package via Conan-generated CMakeDeps
find_package(bstrlib REQUIRED)

add_executable(test_bstrlib test.c)
target_link_libraries(test_bstrlib bstrlib::bstrlib)

enable_testing()
add_test(NAME test_bstrlib COMMAND test_bstrlib)
