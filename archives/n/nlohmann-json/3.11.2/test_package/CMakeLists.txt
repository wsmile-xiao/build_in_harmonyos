cmake_minimum_required(VERSION 3.15)
project(test_nlohmann_json CXX)

# Find the package via Conan-generated CMakeDeps
find_package(nlohmann_json REQUIRED)

add_executable(test_nlohmann_json test.cpp)
target_link_libraries(test_nlohmann_json nlohmann_json::nlohmann_json)
set_target_properties(test_nlohmann_json PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_nlohmann_json COMMAND test_nlohmann_json)
