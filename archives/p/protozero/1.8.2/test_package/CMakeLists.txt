cmake_minimum_required(VERSION 3.15)
project(test_protozero CXX)

# Find the package via Conan-generated CMakeDeps
find_package(protozero REQUIRED)

add_executable(test_protozero test_pbf.cpp)
target_link_libraries(test_protozero protozero::protozero)
target_compile_features(test_protozero PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_protozero COMMAND test_protozero)
