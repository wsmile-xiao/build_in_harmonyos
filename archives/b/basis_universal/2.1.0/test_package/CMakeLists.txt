cmake_minimum_required(VERSION 3.15)
project(test_basisu CXX)

# Find the package via Conan-generated CMakeDeps
find_package(basis_universal REQUIRED)

add_executable(test_basisu basisu_test.cpp)
target_link_libraries(test_basisu basis_universal::basis_universal)

enable_testing()
add_test(NAME test_basisu COMMAND test_basisu)