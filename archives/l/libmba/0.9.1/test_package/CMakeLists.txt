cmake_minimum_required(VERSION 3.15)
project(test_libmba C)

# Find the package via Conan-generated CMakeDeps
find_package(libmba REQUIRED)

add_executable(test_libmba test.c)
target_link_libraries(test_libmba libmba::libmba)

enable_testing()
add_test(NAME test_libmba COMMAND test_libmba)
