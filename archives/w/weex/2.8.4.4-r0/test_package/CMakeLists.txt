cmake_minimum_required(VERSION 3.15)
project(test_weex C)

# Find the package via Conan-generated CMakeDeps
find_package(weex REQUIRED)

add_executable(test_weex test.c)
target_link_libraries(test_weex weex::weex)

enable_testing()
add_test(NAME test_weex COMMAND test_weex)
