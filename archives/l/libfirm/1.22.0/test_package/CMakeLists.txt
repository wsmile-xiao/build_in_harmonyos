cmake_minimum_required(VERSION 3.15)
project(test_libfirm C)

# Find the package via Conan-generated CMakeDeps
find_package(libfirm REQUIRED)

add_executable(test_libfirm test.c)
target_link_libraries(test_libfirm libfirm::libfirm)

enable_testing()
add_test(NAME test_libfirm COMMAND test_libfirm)
