cmake_minimum_required(VERSION 3.15)
project(test_erkir CXX)

# Find the package via Conan-generated CMakeDeps
find_package(erkir CONFIG REQUIRED)

add_executable(test_erkir test_erkir.cpp)
target_link_libraries(test_erkir PRIVATE erkir::erkir)

enable_testing()
add_test(NAME test_erkir_consumer COMMAND test_erkir)
