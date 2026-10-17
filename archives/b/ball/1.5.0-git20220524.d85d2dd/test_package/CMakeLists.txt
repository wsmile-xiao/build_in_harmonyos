cmake_minimum_required(VERSION 3.15)
project(test_ball CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ball REQUIRED)

add_executable(test_ball test.cpp)
target_link_libraries(test_ball ball::ball)

enable_testing()
add_test(NAME test_ball COMMAND test_ball)
