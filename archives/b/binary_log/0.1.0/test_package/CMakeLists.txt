cmake_minimum_required(VERSION 3.15)
project(test_binary_log CXX)

# Find the package via Conan-generated CMakeDeps
find_package(binary_log REQUIRED)

add_executable(test_binary_log test.cpp)
target_link_libraries(test_binary_log binary_log::binary_log)
target_compile_features(test_binary_log PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_binary_log COMMAND test_binary_log)
