cmake_minimum_required(VERSION 3.15)
project(test_dr_mp3 C)

# Find the package via Conan-generated CMakeDeps
find_package(dr_mp3 REQUIRED)

add_executable(test_dr_mp3 test.c)
# dr_mp3 is a single-header library: the implementation is compiled into
# the consumer by defining DR_MP3_IMPLEMENTATION before including dr_mp3.h.
target_compile_definitions(test_dr_mp3 PRIVATE DR_MP3_IMPLEMENTATION)
target_link_libraries(test_dr_mp3 dr_mp3::dr_mp3)

enable_testing()
add_test(NAME test_dr_mp3 COMMAND test_dr_mp3)
