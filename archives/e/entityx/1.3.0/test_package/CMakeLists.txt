cmake_minimum_required(VERSION 3.15)
project(test_entityx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(entityx REQUIRED)

add_executable(test_entityx test_entityx.cpp)
target_link_libraries(test_entityx entityx::entityx)

enable_testing()
add_test(NAME test_entityx COMMAND test_entityx)
