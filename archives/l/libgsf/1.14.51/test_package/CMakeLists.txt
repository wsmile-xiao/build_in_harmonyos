cmake_minimum_required(VERSION 3.15)
project(test_libgsf C)

# Find the package via Conan-generated CMakeDeps
find_package(libgsf REQUIRED)

add_executable(test_libgsf test.c)
target_link_libraries(test_libgsf libgsf::libgsf)

enable_testing()
add_test(NAME test_libgsf COMMAND test_libgsf)
