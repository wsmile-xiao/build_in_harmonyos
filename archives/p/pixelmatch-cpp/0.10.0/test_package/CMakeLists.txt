cmake_minimum_required(VERSION 3.15)
project(test_pixelmatch_cpp CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(pixelmatch-cpp REQUIRED CONFIG)

add_executable(test_pixelmatch_cpp test.cpp)
target_link_libraries(test_pixelmatch_cpp pixelmatch-cpp::pixelmatch-cpp)

enable_testing()
add_test(NAME test_pixelmatch_cpp COMMAND test_pixelmatch_cpp)
