cmake_minimum_required(VERSION 3.15)
project(test_wasm3 C)

# Find the package via Conan-generated CMakeDeps
find_package(wasm3 REQUIRED)

add_executable(test_wasm3 test.c)
target_link_libraries(test_wasm3 wasm3::wasm3)

enable_testing()
add_test(NAME test_wasm3 COMMAND test_wasm3)
