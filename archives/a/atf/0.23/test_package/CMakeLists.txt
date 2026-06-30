cmake_minimum_required(VERSION 3.15)
project(test_atf C)

# Find the package via Conan-generated CMakeDeps
find_package(atf REQUIRED)

add_executable(test_atf test.c)
target_link_libraries(test_atf atf::atf)

enable_testing()
add_test(NAME test_atf_pass COMMAND test_atf pass_test)
add_test(NAME test_atf_str_compare COMMAND test_atf str_compare_test)
add_test(NAME test_atf_math COMMAND test_atf math_test)
