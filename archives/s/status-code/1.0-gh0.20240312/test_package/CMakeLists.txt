cmake_minimum_required(VERSION 3.15)
project(test_generic_code CXX)

# Find the package via Conan-generated CMakeDeps
find_package(status-code REQUIRED)

add_executable(test_generic_code test_generic_code.cpp)
target_link_libraries(test_generic_code status-code::status-code)
set_target_properties(test_generic_code PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_generic_code COMMAND test_generic_code)
