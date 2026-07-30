cmake_minimum_required(VERSION 3.15)
project(test_draco CXX)

# Find the package via Conan-generated CMakeDeps
find_package(draco REQUIRED)

add_executable(test_draco test.cpp)
target_link_libraries(test_draco draco::draco)
target_compile_features(test_draco PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_draco COMMAND test_draco)