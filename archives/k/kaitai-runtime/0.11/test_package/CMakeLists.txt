cmake_minimum_required(VERSION 3.15)
project(test_kaitai-runtime CXX)

# Find the package via Conan-generated CMakeDeps
find_package(kaitai-runtime REQUIRED)

add_executable(test_kaitai-runtime test.cpp)
target_link_libraries(test_kaitai-runtime kaitai-runtime::kaitai-runtime)

enable_testing()
add_test(NAME test_kaitai-runtime COMMAND test_kaitai-runtime)
