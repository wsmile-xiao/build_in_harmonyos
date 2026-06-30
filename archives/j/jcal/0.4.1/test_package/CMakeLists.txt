cmake_minimum_required(VERSION 3.15)
project(test_jcal C)

# Find the package via Conan-generated CMakeDeps
find_package(jcal REQUIRED)

add_executable(test_jcal test.c)
target_link_libraries(test_jcal jcal::jcal)

enable_testing()
add_test(NAME test_jcal COMMAND test_jcal)
