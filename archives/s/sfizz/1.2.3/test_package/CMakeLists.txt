cmake_minimum_required(VERSION 3.15)
project(test_sfizz C)

# Find the package via Conan-generated CMakeDeps
find_package(sfizz REQUIRED)

add_executable(test_sfizz test.c)
target_link_libraries(test_sfizz sfizz::sfizz)

enable_testing()
add_test(NAME test_sfizz COMMAND test_sfizz)
