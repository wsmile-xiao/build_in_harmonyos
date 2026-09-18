cmake_minimum_required(VERSION 3.15)
project(kytea_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# Library consumer: find_package via Conan-generated CMakeDeps
find_package(kytea CONFIG REQUIRED)

add_executable(kytea_lib_test test.cpp)
target_link_libraries(kytea_lib_test PRIVATE kytea::kytea)
