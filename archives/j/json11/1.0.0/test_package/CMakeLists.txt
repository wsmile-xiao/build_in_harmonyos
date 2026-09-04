cmake_minimum_required(VERSION 3.15)
project(test_json11 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(json11 REQUIRED)

add_executable(test_json11 test.cpp)
target_link_libraries(test_json11 json11::json11)

enable_testing()
add_test(NAME test_json11 COMMAND test_json11)