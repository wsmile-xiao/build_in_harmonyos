cmake_minimum_required(VERSION 3.15)
project(test_stb_image_resize C)

# Find the package via Conan-generated CMakeDeps
find_package(stb_image_resize REQUIRED)

add_executable(test_stb_image_resize test.c)
target_link_libraries(test_stb_image_resize stb::image_resize)

enable_testing()
add_test(NAME test_stb_image_resize COMMAND test_stb_image_resize)
