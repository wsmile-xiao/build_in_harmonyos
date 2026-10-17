cmake_minimum_required(VERSION 3.15)
project(test_dynamite C)

# Find the package via Conan-generated CMakeDeps
find_package(dynamite REQUIRED)

add_executable(test_dynamite test.c)
target_link_libraries(test_dynamite dynamite::dynamite)

enable_testing()
add_test(NAME test_dynamite COMMAND test_dynamite)
