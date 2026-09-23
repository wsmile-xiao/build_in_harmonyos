cmake_minimum_required(VERSION 3.15)
project(test_readerwriterqueue CXX)

# Find the package via Conan-generated CMakeDeps
find_package(readerwriterqueue REQUIRED)

add_executable(test_readerwriterqueue test.cpp)
target_link_libraries(test_readerwriterqueue readerwriterqueue::readerwriterqueue)

enable_testing()
add_test(NAME test_readerwriterqueue COMMAND test_readerwriterqueue)
