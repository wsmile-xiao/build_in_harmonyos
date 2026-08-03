cmake_minimum_required(VERSION 3.15)
project(test_media-control C)

# Find the package via Conan-generated CMakeDeps
find_package(media-control REQUIRED)

add_executable(test_media-control test.c)
target_link_libraries(test_media-control media-control::media-control)

enable_testing()
add_test(NAME test_media-control COMMAND test_media-control)