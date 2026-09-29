cmake_minimum_required(VERSION 3.15)
project(test_microgl CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(microgl REQUIRED CONFIG)

add_executable(test_microgl test_microgl.cpp)
target_link_libraries(test_microgl microgl::microgl)

enable_testing()
add_test(NAME test_microgl COMMAND test_microgl)