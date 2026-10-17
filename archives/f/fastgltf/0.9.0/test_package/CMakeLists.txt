cmake_minimum_required(VERSION 3.15)
project(test_fastgltf CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fastgltf REQUIRED)

add_executable(test_fastgltf test.cpp)
target_link_libraries(test_fastgltf fastgltf::fastgltf)
target_compile_features(test_fastgltf PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_fastgltf COMMAND test_fastgltf)