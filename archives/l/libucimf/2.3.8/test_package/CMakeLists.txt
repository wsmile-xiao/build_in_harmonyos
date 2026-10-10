cmake_minimum_required(VERSION 3.15)
project(test_libucimf C)

# Find the package via Conan-generated CMakeDeps
find_package(libucimf REQUIRED)

add_executable(test_libucimf test.c)
target_link_libraries(test_libucimf libucimf::libucimf)

enable_testing()
add_test(NAME test_libucimf COMMAND test_libucimf)
