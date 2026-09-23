cmake_minimum_required(VERSION 3.15)
project(test_tpl C)

# Find the package via Conan-generated CMakeDeps
find_package(tpl REQUIRED)

add_executable(test_tpl test.c)
target_link_libraries(test_tpl tpl::tpl)

enable_testing()
add_test(NAME test_tpl COMMAND test_tpl)
