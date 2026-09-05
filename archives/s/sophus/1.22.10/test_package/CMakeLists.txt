cmake_minimum_required(VERSION 3.15)
project(test_sophus CXX)

# Find the package via Conan-generated CMakeDeps
find_package(Sophus REQUIRED)

add_executable(test_sophus test.cpp)
target_link_libraries(test_sophus Sophus::Sophus)

enable_testing()
add_test(NAME test_sophus COMMAND test_sophus)
