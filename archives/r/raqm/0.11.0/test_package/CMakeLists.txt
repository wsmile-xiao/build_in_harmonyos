cmake_minimum_required(VERSION 3.15)
project(test_raqm C)

# Find the package via Conan-generated CMakeDeps. freetype is an explicit
# dependency of the consumer: raqm.h includes <ft2build.h> directly, and
# the freetype CMakeDeps target carries the freetype2 include directory.
find_package(raqm REQUIRED)
find_package(freetype REQUIRED)

add_executable(test_raqm test.c)
target_link_libraries(test_raqm raqm::raqm freetype::freetype)

enable_testing()
add_test(NAME test_raqm COMMAND test_raqm)
