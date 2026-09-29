cmake_minimum_required(VERSION 3.15)
project(test_librime CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(rime REQUIRED)

add_executable(test_librime test.cpp)
target_link_libraries(test_librime rime::rime)

enable_testing()
add_test(NAME test_librime COMMAND test_librime)
