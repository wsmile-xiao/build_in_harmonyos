cmake_minimum_required(VERSION 3.15)
project(test_stdex CXX)

# Find the package via Conan-generated CMakeDeps
find_package(stdex REQUIRED)

add_executable(test_stdex test.cpp)
target_link_libraries(test_stdex stdex::stdex)

enable_testing()
add_test(NAME test_stdex COMMAND test_stdex)