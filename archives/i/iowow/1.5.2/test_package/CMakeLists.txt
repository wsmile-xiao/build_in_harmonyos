cmake_minimum_required(VERSION 3.15)
project(test_iowow C)

# Find the package via Conan-generated CMakeDeps
find_package(iowow REQUIRED)

add_executable(test_iowow test.c)
target_link_libraries(test_iowow iowow::iowow)

enable_testing()
add_test(NAME test_iowow COMMAND test_iowow)
