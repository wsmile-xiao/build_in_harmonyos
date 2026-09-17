cmake_minimum_required(VERSION 3.15)
project(test_eaassert CXX)

# Find the package via Conan-generated CMakeDeps
find_package(eaassert REQUIRED)

add_executable(test_eaassert test.cpp)
target_link_libraries(test_eaassert eaassert::eaassert)

enable_testing()
add_test(NAME test_eaassert COMMAND test_eaassert)