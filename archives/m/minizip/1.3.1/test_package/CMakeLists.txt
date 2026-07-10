cmake_minimum_required(VERSION 3.15)
project(test_minizip C)

# Find the package via Conan-generated CMakeDeps
find_package(minizip REQUIRED)

add_executable(test_minizip test.c)
target_link_libraries(test_minizip minizip::minizip)

enable_testing()
add_test(NAME test_minizip COMMAND test_minizip)
