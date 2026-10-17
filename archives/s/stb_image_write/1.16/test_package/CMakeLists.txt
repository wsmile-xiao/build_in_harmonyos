cmake_minimum_required(VERSION 3.15)
project(test_stb_image_write C)

# Find the package via Conan-generated CMakeDeps
find_package(stb_image_write REQUIRED)

add_executable(test_stb_image_write test.c)
target_link_libraries(test_stb_image_write stb_image_write::stb_image_write)

enable_testing()
add_test(NAME test_stb_image_write COMMAND test_stb_image_write)
