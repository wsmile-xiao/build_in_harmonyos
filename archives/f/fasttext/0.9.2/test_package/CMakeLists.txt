cmake_minimum_required(VERSION 3.15)
project(test_fasttext CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fasttext REQUIRED)

add_executable(test_fasttext test.cpp)
target_link_libraries(test_fasttext fasttext::fasttext)

enable_testing()
add_test(NAME test_fasttext COMMAND test_fasttext)