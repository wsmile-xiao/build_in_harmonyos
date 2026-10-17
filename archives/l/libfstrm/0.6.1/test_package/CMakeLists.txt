cmake_minimum_required(VERSION 3.15)
project(test_libfstrm C)

# Find the package via Conan-generated CMakeDeps
find_package(libfstrm REQUIRED)

add_executable(test_libfstrm test.c)
target_link_libraries(test_libfstrm libfstrm::libfstrm)

enable_testing()
add_test(NAME test_libfstrm COMMAND test_libfstrm)
