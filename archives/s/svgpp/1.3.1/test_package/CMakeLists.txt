cmake_minimum_required(VERSION 3.15)
project(svgpp_test_package CXX)

# Conan-generated package configuration (CMakeDeps).
find_package(svgpp CONFIG REQUIRED)

add_executable(test_svgpp test_svgpp.cpp)
target_link_libraries(test_svgpp PRIVATE svgpp::svgpp)
target_compile_features(test_svgpp PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_svgpp COMMAND test_svgpp)
