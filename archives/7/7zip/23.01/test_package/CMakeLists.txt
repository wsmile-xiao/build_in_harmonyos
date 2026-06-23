cmake_minimum_required(VERSION 3.15)
project(test_7zip C)

# Find the package via Conan-generated CMakeDeps
find_package(7zip REQUIRED)

add_executable(test_7zip test.c)
target_link_libraries(test_7zip 7zip::7zip)

enable_testing()
add_test(NAME test_7zip COMMAND test_7zip)
