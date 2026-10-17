cmake_minimum_required(VERSION 3.15)
project(test_libinjection C)

# Find the package via Conan-generated CMakeDeps
find_package(libinjection REQUIRED)

add_executable(test_libinjection test.c)
target_link_libraries(test_libinjection libinjection::libinjection)

enable_testing()
add_test(NAME test_libinjection COMMAND test_libinjection)
