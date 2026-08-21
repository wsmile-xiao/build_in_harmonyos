cmake_minimum_required(VERSION 3.15)
project(test_zix C)

# Find the package via Conan-generated CMakeDeps
find_package(zix REQUIRED)

add_executable(test_zix test.c)
target_link_libraries(test_zix zix::zix)

enable_testing()
add_test(NAME test_zix COMMAND test_zix)
