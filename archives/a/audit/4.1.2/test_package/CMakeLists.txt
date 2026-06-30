cmake_minimum_required(VERSION 3.15)
project(test_audit C)

# Find the package via Conan-generated CMakeDeps
find_package(audit REQUIRED)

add_executable(test_audit test.c)
target_link_libraries(test_audit audit::audit)

enable_testing()
add_test(NAME test_audit COMMAND test_audit)
