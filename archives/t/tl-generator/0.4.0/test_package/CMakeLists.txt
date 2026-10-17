cmake_minimum_required(VERSION 3.15)
project(test_tl-generator CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tl-generator REQUIRED)

add_executable(test_tl-generator test.cpp)
target_link_libraries(test_tl-generator tl::generator)
set_target_properties(test_tl-generator PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_tl-generator COMMAND test_tl-generator)