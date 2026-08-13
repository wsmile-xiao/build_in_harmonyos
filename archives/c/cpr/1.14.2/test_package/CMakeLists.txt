cmake_minimum_required(VERSION 3.15)
project(test_cpr CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpr REQUIRED)

add_executable(test_cpr test.cpp)
target_link_libraries(test_cpr PRIVATE cpr::cpr)
target_compile_features(test_cpr PRIVATE cxx_std_17)
