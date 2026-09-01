cmake_minimum_required(VERSION 3.15)
project(test_lexy CXX)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name=lexy, target=foonathan::lexy)
find_package(lexy REQUIRED)

add_executable(test_lexy test_lexy.cpp)
target_link_libraries(test_lexy PRIVATE foonathan::lexy)
target_compile_features(test_lexy PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_lexy COMMAND test_lexy)
