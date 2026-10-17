cmake_minimum_required(VERSION 3.15)
project(test_arduinojson CXX)

# Find the package via Conan-generated CMakeDeps
find_package(arduinojson REQUIRED)

add_executable(test_arduinojson test.cpp)
target_link_libraries(test_arduinojson arduinojson::arduinojson)

enable_testing()
add_test(NAME test_arduinojson COMMAND test_arduinojson)