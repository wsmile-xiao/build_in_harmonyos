cmake_minimum_required(VERSION 3.15)
project(test_json_dto CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(json-dto REQUIRED)

add_executable(test_json_dto test_json_dto.cpp)
target_link_libraries(test_json_dto json-dto::json-dto)

enable_testing()
add_test(NAME test_json_dto COMMAND test_json_dto)