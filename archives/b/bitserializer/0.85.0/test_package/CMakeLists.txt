cmake_minimum_required(VERSION 3.15)
project(test_bitserializer CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bitserializer REQUIRED)

add_executable(test_bitserializer test.cpp)
target_link_libraries(test_bitserializer BitSerializer::core)
target_compile_features(test_bitserializer PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_bitserializer COMMAND test_bitserializer)
