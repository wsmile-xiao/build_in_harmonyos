cmake_minimum_required(VERSION 3.15)
project(test_fastmod CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(fastmod CONFIG REQUIRED)

add_executable(test_fastmod test.cpp)
target_link_libraries(test_fastmod fastmod::fastmod)

enable_testing()
add_test(NAME test_fastmod COMMAND test_fastmod)
