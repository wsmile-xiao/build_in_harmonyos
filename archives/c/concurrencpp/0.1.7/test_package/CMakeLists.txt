cmake_minimum_required(VERSION 3.15)
project(test_concurrencpp LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(concurrencpp REQUIRED)

add_executable(test_concurrencpp test.cpp)
target_link_libraries(test_concurrencpp PRIVATE concurrencpp::concurrencpp)
target_compile_features(test_concurrencpp PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_concurrencpp COMMAND test_concurrencpp)