cmake_minimum_required(VERSION 3.15)
project(test_xmlbird C)

# Find the package via Conan-generated CMakeDeps
find_package(xmlbird REQUIRED)

add_executable(test_xmlbird test.c)
target_link_libraries(test_xmlbird xmlbird::xmlbird)

enable_testing()
add_test(NAME test_xmlbird COMMAND test_xmlbird)
