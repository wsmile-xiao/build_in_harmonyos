cmake_minimum_required(VERSION 3.15)
project(test_xenium CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(xenium REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_xenium test.cpp)
target_link_libraries(test_xenium xenium::xenium Threads::Threads)

enable_testing()
add_test(NAME test_xenium COMMAND test_xenium)
