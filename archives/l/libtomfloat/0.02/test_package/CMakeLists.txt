cmake_minimum_required(VERSION 3.15)
project(test_libtomfloat C)

# Find the package via Conan-generated CMakeDeps.
# libtommath is linked explicitly: tomfloat.h includes <tommath.h>, so the
# test translation unit consumes its headers transitively.
find_package(libtomfloat REQUIRED)
find_package(libtommath REQUIRED)

add_executable(test_libtomfloat test.c)
target_link_libraries(test_libtomfloat libtomfloat::libtomfloat libtommath::libtommath)

enable_testing()
add_test(NAME test_libtomfloat COMMAND test_libtomfloat)
