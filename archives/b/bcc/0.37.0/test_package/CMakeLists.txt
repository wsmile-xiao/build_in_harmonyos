cmake_minimum_required(VERSION 3.15)
project(test_bcc C)

# Find the package via Conan-generated CMakeDeps
find_package(bcc REQUIRED)

add_executable(test_bcc test.c)
target_link_libraries(test_bcc bcc::bcc)

enable_testing()
add_test(NAME test_bcc COMMAND test_bcc)
