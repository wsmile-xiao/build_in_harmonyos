cmake_minimum_required(VERSION 3.15)
project(test_lief CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lief REQUIRED)

add_executable(test_lief test_lief.cpp)
target_link_libraries(test_lief lief::lief)
target_compile_features(test_lief PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_lief COMMAND test_lief)
