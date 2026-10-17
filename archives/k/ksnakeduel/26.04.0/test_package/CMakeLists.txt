cmake_minimum_required(VERSION 3.15)
project(test_ksnakeduel C)

# Find the package via Conan-generated CMakeDeps
find_package(ksnakeduel REQUIRED)

add_executable(test_ksnakeduel test.c)
target_link_libraries(test_ksnakeduel ksnakeduel::ksnakeduel)

enable_testing()
add_test(NAME test_ksnakeduel COMMAND test_ksnakeduel)
