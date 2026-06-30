cmake_minimum_required(VERSION 3.15)
project(test_libucl C)

# Find the package via Conan-generated CMakeDeps
find_package(libucl REQUIRED)

add_executable(test_libucl test.c)
target_link_libraries(test_libucl libucl::libucl)

enable_testing()
add_test(NAME test_libucl COMMAND test_libucl)
