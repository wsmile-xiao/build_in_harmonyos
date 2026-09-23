cmake_minimum_required(VERSION 3.15)
project(test_mmkv CXX)

set(CMAKE_CXX_STANDARD 20)

# Find the mmkv package via Conan-generated CMakeDeps
find_package(mmkv REQUIRED)

add_executable(test_mmkv test_mmkv.cpp)
target_link_libraries(test_mmkv mmkv::mmkv)

enable_testing()
add_test(NAME test_mmkv COMMAND test_mmkv)
