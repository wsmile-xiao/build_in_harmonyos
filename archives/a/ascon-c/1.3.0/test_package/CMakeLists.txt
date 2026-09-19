cmake_minimum_required(VERSION 3.15)
project(test_ascon-c C)

# Find the package via Conan-generated CMakeDeps
find_package(ascon-c REQUIRED)

add_executable(test_ascon-c test.c)
# Link the combined AEAD+HASH reference implementation component.
target_link_libraries(test_ascon-c ascon-c::asconv13)

enable_testing()
add_test(NAME test_ascon-c COMMAND test_ascon-c)
