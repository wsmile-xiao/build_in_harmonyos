cmake_minimum_required(VERSION 3.15)
project(test_mailtutan C)

# Find the package via Conan-generated CMakeDeps
find_package(mailtutan REQUIRED)

add_executable(test_mailtutan test.c)
target_link_libraries(test_mailtutan mailtutan::mailtutan)

enable_testing()
add_test(NAME test_mailtutan COMMAND test_mailtutan)
