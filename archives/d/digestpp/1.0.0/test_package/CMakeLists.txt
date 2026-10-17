cmake_minimum_required(VERSION 3.15)
project(test_digestpp LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(digestpp CONFIG REQUIRED)

add_executable(test_digestpp test_digestpp.cpp)
target_link_libraries(test_digestpp PRIVATE digestpp::digestpp)
set_target_properties(test_digestpp PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

enable_testing()
add_test(NAME test_digestpp COMMAND test_digestpp)