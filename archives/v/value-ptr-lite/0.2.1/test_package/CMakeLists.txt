cmake_minimum_required(VERSION 3.15)
project(test_value-ptr-lite CXX)

# Find the package via Conan-generated CMakeDeps
find_package(value-ptr-lite REQUIRED)

add_executable(test_value-ptr-lite test_package.cpp)
target_link_libraries(test_value-ptr-lite value-ptr-lite::value-ptr-lite)

enable_testing()
add_test(NAME test_value-ptr-lite COMMAND test_value-ptr-lite)
