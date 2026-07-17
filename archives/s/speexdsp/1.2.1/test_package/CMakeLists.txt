cmake_minimum_required(VERSION 3.15)
project(test_speexdsp C)

# Find the package via Conan-generated CMakeDeps
find_package(speexdsp REQUIRED)

add_executable(test_speexdsp test.c)
target_link_libraries(test_speexdsp speexdsp::speexdsp)

enable_testing()
add_test(NAME test_speexdsp COMMAND test_speexdsp)
