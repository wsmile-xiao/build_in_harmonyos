cmake_minimum_required(VERSION 3.15)
project(test_argy CXX)

# Find the package via Conan-generated CMakeDeps
find_package(argy REQUIRED)

add_executable(test_argy test.cpp)
target_link_libraries(test_argy argy::argy)
target_compile_features(test_argy PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_argy COMMAND test_argy)
