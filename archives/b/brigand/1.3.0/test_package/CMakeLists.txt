cmake_minimum_required(VERSION 3.15)
project(test_brigand CXX)

# Find the package via Conan-generated CMakeDeps
find_package(brigand REQUIRED)

add_executable(test_brigand test.cpp)
target_link_libraries(test_brigand brigand::brigand)
set_target_properties(test_brigand PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_brigand COMMAND test_brigand)
