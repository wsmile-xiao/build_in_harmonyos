cmake_minimum_required(VERSION 3.15)
project(test_strong_type CXX)

# Find the package via Conan-generated CMakeDeps
find_package(strong-type REQUIRED)

add_executable(test_strong_type test_strong_type.cpp)
target_link_libraries(test_strong_type strong-type::strong-type)
set_target_properties(test_strong_type PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_strong_type COMMAND test_strong_type)
