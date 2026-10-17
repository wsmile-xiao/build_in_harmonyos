cmake_minimum_required(VERSION 3.15)
project(test_tinyformat CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tinyformat REQUIRED)

add_executable(test_tinyformat test.cpp)
target_link_libraries(test_tinyformat tinyformat::tinyformat)
target_compile_features(test_tinyformat PRIVATE cxx_std_17)
