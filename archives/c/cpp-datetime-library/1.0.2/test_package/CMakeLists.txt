cmake_minimum_required(VERSION 3.15)
project(test_cpp-datetime-library CXX)

# Find the package via Conan-generated CMakeDeps
find_package(datetime REQUIRED)

add_executable(test_cpp-datetime-library test.cpp)
target_link_libraries(test_cpp-datetime-library datetime::datetime)

enable_testing()
add_test(NAME test_cpp-datetime-library COMMAND test_cpp-datetime-library)
