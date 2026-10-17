cmake_minimum_required(VERSION 3.15)
project(test_libscrypt C)

# Find the package via Conan-generated CMakeDeps
find_package(libscrypt REQUIRED)

add_executable(test_libscrypt test.c)
target_link_libraries(test_libscrypt libscrypt::libscrypt)

enable_testing()
add_test(NAME test_libscrypt COMMAND test_libscrypt)
