cmake_minimum_required(VERSION 3.15)
project(test_cgicc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cgicc REQUIRED)

add_executable(test_cgicc test.cpp)
target_link_libraries(test_cgicc cgicc::cgicc)

enable_testing()
add_test(NAME test_cgicc COMMAND test_cgicc)