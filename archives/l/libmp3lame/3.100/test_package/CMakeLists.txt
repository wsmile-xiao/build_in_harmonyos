cmake_minimum_required(VERSION 3.15)
project(test_libmp3lame C)

# Find the package via Conan-generated CMakeDeps
find_package(libmp3lame REQUIRED)

add_executable(test_libmp3lame test.c)
target_link_libraries(test_libmp3lame libmp3lame::libmp3lame)

enable_testing()
add_test(NAME test_libmp3lame COMMAND test_libmp3lame)
