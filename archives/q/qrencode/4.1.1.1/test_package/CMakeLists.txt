cmake_minimum_required(VERSION 3.15)
project(test_qrencode C)

# Find the package via Conan-generated CMakeDeps
find_package(qrencode REQUIRED)

add_executable(test_qrencode test.c)
target_link_libraries(test_qrencode qrencode::qrencode)

enable_testing()
add_test(NAME test_qrencode COMMAND test_qrencode)
