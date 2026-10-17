cmake_minimum_required(VERSION 3.15)
project(test_motti CXX)

# Find the package via Conan-generated CMakeDeps
find_package(motti REQUIRED)

add_executable(test_motti test.cpp)
target_link_libraries(test_motti motti::motti)

enable_testing()
add_test(NAME test_motti COMMAND test_motti)
