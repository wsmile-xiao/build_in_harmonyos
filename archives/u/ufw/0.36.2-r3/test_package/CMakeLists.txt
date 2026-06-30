cmake_minimum_required(VERSION 3.15)
project(test_ufw C)

# Find the package via Conan-generated CMakeDeps
find_package(ufw REQUIRED)

add_executable(test_ufw test.c)
target_link_libraries(test_ufw ufw::ufw)

enable_testing()
add_test(NAME test_ufw COMMAND test_ufw)
