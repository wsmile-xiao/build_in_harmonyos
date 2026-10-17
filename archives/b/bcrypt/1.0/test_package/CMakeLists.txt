cmake_minimum_required(VERSION 3.15)
project(test_bcrypt C)

# Find the package via Conan-generated CMakeDeps
find_package(bcrypt REQUIRED)

add_executable(test_bcrypt test.c)
target_link_libraries(test_bcrypt bcrypt::bcrypt)

enable_testing()
add_test(NAME test_bcrypt COMMAND test_bcrypt)
