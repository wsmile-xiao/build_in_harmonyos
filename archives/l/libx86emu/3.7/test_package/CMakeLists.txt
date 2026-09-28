cmake_minimum_required(VERSION 3.15)
project(test_libx86emu C)

# Find the package via Conan-generated CMakeDeps
find_package(libx86emu REQUIRED)

add_executable(test_libx86emu test.c)
target_link_libraries(test_libx86emu libx86emu::libx86emu)

enable_testing()
add_test(NAME test_libx86emu COMMAND test_libx86emu)
