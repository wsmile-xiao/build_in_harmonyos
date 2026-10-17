cmake_minimum_required(VERSION 3.15)
project(test_gles2 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gles2 REQUIRED)

add_executable(test_gles2 test.cpp)
target_link_libraries(test_gles2 gles2::gles2)

enable_testing()
add_test(NAME test_gles2 COMMAND test_gles2)
