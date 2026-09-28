cmake_minimum_required(VERSION 3.15)
project(test_lcc C)

# Find the package via Conan-generated CMakeDeps
find_package(lcc REQUIRED)

add_executable(test_lcc test.c)
target_link_libraries(test_lcc lcc::lcc)

enable_testing()
add_test(NAME test_lcc COMMAND test_lcc)
