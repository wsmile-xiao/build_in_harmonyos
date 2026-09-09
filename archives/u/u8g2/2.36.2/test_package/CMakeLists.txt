cmake_minimum_required(VERSION 3.15)
project(test_u8g2 C)

# Find the package via Conan-generated CMakeDeps
find_package(u8g2 REQUIRED)

add_executable(test_u8g2 test.c)
target_link_libraries(test_u8g2 u8g2::u8g2)

enable_testing()
add_test(NAME test_u8g2 COMMAND test_u8g2)
