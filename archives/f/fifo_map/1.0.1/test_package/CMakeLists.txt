cmake_minimum_required(VERSION 3.15)
project(test_fifo_map CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fifo_map REQUIRED)

add_executable(test_fifo_map test.cpp)
target_link_libraries(test_fifo_map fifo_map::fifo_map)

enable_testing()
add_test(NAME test_fifo_map COMMAND test_fifo_map)