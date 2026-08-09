cmake_minimum_required(VERSION 3.15)
project(test_mfem CXX)

# Find the package via Conan-generated CMakeDeps
find_package(MFEM REQUIRED)

add_executable(test_mfem test.cpp)
target_link_libraries(test_mfem mfem)

enable_testing()
add_test(NAME test_mfem COMMAND test_mfem)
