cmake_minimum_required(VERSION 3.15)
project(test_heinz CXX)

# Find the package via Conan-generated CMakeDeps
find_package(LibHeinz REQUIRED)

add_executable(test_heinz test_heinz.cpp)
target_link_libraries(test_heinz LibHeinz::LibHeinz)
# libheinz requires C++20 (concepts); force it regardless of global standard.
target_compile_features(test_heinz PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_heinz COMMAND test_heinz)
