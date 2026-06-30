cmake_minimum_required(VERSION 3.15)
project(test_dog C)

# Find the package via Conan-generated CMakeDeps
find_package(dog REQUIRED)

add_executable(test_dog test.c)
target_link_libraries(test_dog dog::dog)

enable_testing()
add_test(NAME test_dog COMMAND test_dog)
