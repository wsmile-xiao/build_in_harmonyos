cmake_minimum_required(VERSION 3.15)
project(test_confu_json CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(confu_json REQUIRED)

add_executable(test_confu_json test.cpp)
target_link_libraries(test_confu_json confu_json::confu_json)

enable_testing()
add_test(NAME test_confu_json COMMAND test_confu_json)
