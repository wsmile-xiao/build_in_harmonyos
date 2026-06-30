cmake_minimum_required(VERSION 3.15)
project(test_piknik C)

# Find the package via Conan-generated CMakeDeps
find_package(piknik REQUIRED)

add_executable(test_piknik test.c)
target_link_libraries(test_piknik piknik::piknik)

enable_testing()
add_test(NAME test_piknik COMMAND test_piknik)
