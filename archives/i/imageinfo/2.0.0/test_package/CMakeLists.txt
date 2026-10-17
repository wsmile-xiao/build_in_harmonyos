cmake_minimum_required(VERSION 3.15)
project(test_imageinfo CXX)

# Find the package via Conan-generated CMakeDeps
find_package(imageinfo REQUIRED)

add_executable(test_imageinfo test.cpp)
target_link_libraries(test_imageinfo imageinfo::imageinfo)

enable_testing()
add_test(NAME test_imageinfo COMMAND test_imageinfo)
