cmake_minimum_required(VERSION 3.15)
project(test_ace CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ace REQUIRED)

add_executable(test_ace test.cpp)
target_link_libraries(test_ace ace::ace)

enable_testing()
add_test(NAME test_ace COMMAND test_ace)
