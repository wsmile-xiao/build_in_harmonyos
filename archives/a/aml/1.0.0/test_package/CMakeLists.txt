cmake_minimum_required(VERSION 3.15)
project(test_aml C)

# Find the package via Conan-generated CMakeDeps
find_package(aml REQUIRED)

add_executable(test_aml test.c)
target_link_libraries(test_aml aml::aml)

enable_testing()
add_test(NAME test_aml COMMAND test_aml)
