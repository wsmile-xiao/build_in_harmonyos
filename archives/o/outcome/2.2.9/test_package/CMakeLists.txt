cmake_minimum_required(VERSION 3.15)
project(test_outcome CXX)

# Find the package via Conan-generated CMakeDeps
find_package(outcome REQUIRED)

add_executable(test_outcome test_outcome.cpp)
target_link_libraries(test_outcome outcome::outcome)
set_target_properties(test_outcome PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_outcome COMMAND test_outcome)
