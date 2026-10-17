cmake_minimum_required(VERSION 3.15)
project(test_jsoncons CXX)

# Find the package via Conan-generated CMakeDeps
find_package(jsoncons REQUIRED)

add_executable(test_jsoncons test_jsoncons.cpp)
target_link_libraries(test_jsoncons jsoncons::jsoncons)
set_target_properties(test_jsoncons PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_jsoncons COMMAND test_jsoncons)