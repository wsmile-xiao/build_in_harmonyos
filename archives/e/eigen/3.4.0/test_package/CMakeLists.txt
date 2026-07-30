cmake_minimum_required(VERSION 3.15)
project(test_eigen CXX)

# Find the package via Conan-generated CMakeDeps
find_package(Eigen3 REQUIRED)

add_executable(test_eigen test.cpp)
target_link_libraries(test_eigen Eigen3::Eigen)

enable_testing()
add_test(NAME test_eigen COMMAND test_eigen)
