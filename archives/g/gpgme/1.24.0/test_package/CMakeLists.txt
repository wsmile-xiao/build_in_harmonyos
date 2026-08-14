cmake_minimum_required(VERSION 3.15)
project(test_gpgme C)

# Find the package via Conan-generated CMakeDeps
find_package(gpgme REQUIRED)

add_executable(test_gpgme test.c)
target_link_libraries(test_gpgme gpgme::gpgme)

enable_testing()
add_test(NAME test_gpgme COMMAND test_gpgme)
