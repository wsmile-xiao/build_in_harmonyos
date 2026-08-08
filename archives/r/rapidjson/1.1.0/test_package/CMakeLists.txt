cmake_minimum_required(VERSION 3.15)
project(test_rapidjson CXX)

# Find the package via Conan-generated CMakeDeps
find_package(RapidJSON REQUIRED)

add_executable(test_rapidjson test_package.cpp)
target_link_libraries(test_rapidjson RapidJSON::RapidJSON)

enable_testing()
add_test(NAME test_rapidjson COMMAND test_rapidjson)