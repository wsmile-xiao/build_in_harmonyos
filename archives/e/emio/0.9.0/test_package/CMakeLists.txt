cmake_minimum_required(VERSION 3.15)
project(test_emio CXX)

# Find the package via Conan-generated CMakeDeps
find_package(emio REQUIRED)

add_executable(test_emio test.cpp)
target_compile_features(test_emio PRIVATE cxx_std_20)
target_link_libraries(test_emio emio::emio)

enable_testing()
add_test(NAME test_emio COMMAND test_emio)