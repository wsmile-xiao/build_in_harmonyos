cmake_minimum_required(VERSION 3.15)
project(test_miniscript CXX)

# Find the package via Conan-generated CMakeDeps
find_package(miniscript REQUIRED)

add_executable(test_miniscript test.cpp)
target_link_libraries(test_miniscript miniscript::miniscript)

enable_testing()
add_test(NAME test_miniscript COMMAND test_miniscript)
