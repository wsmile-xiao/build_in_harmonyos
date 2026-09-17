cmake_minimum_required(VERSION 3.15)
project(test_libmalcontent C)

# Find the package via Conan-generated CMakeDeps
find_package(malcontent-0 REQUIRED)

add_executable(test_libmalcontent test.c)
target_link_libraries(test_libmalcontent malcontent-0::malcontent-0)

enable_testing()
add_test(NAME test_libmalcontent COMMAND test_libmalcontent)
