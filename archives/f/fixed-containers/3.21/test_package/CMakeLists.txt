cmake_minimum_required(VERSION 3.15)
project(test_fixed-containers CXX)

# fixed-containers 是 C++20 库（concepts/compare 等），消费者也必须 C++20
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find the package via Conan-generated CMakeDeps
find_package(fixed_containers CONFIG REQUIRED)

add_executable(test_fixed-containers test.cpp)
target_link_libraries(test_fixed-containers PRIVATE fixed_containers::fixed_containers)

enable_testing()
add_test(NAME test_fixed-containers COMMAND test_fixed-containers)