cmake_minimum_required(VERSION 3.15)
project(test_liblockfile C)

# Find the package via Conan-generated CMakeDeps
find_package(liblockfile REQUIRED)

add_executable(test_liblockfile test.c)
target_link_libraries(test_liblockfile liblockfile::liblockfile)

enable_testing()
add_test(NAME test_liblockfile COMMAND test_liblockfile)
