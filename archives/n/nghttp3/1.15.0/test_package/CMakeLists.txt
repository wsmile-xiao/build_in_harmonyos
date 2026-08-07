cmake_minimum_required(VERSION 3.15)
project(test_nghttp3 C)

# Find the package via Conan-generated CMakeDeps
find_package(nghttp3 REQUIRED)

add_executable(test_nghttp3 test.c)
target_link_libraries(test_nghttp3 nghttp3::nghttp3)

enable_testing()
add_test(NAME test_nghttp3 COMMAND test_nghttp3)
