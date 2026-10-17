cmake_minimum_required(VERSION 3.15)
project(test_valijson CXX)

# Find the package via Conan-generated CMakeDeps
find_package(valijson REQUIRED)

add_executable(test_valijson test_valijson.cpp)
target_link_libraries(test_valijson valijson::valijson)

enable_testing()
add_test(NAME test_valijson COMMAND test_valijson)