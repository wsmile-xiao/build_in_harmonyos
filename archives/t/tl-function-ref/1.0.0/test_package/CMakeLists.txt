cmake_minimum_required(VERSION 3.15)
project(test_tl-function-ref LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tl-function-ref REQUIRED)

add_executable(test_tl-function-ref test_tl-function-ref.cpp)
target_link_libraries(test_tl-function-ref tl::function_ref)
target_compile_features(test_tl-function-ref PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_tl-function-ref COMMAND test_tl-function-ref)
