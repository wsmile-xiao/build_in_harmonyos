cmake_minimum_required(VERSION 3.15)
project(test_rapidyaml CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = "ryml")
find_package(ryml REQUIRED)

add_executable(test_rapidyaml main.cpp)
target_link_libraries(test_rapidyaml PRIVATE ryml::ryml)

enable_testing()
add_test(NAME test_rapidyaml COMMAND test_rapidyaml)
